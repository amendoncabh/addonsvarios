# # -*- coding: utf-8 -*-
#
# from odoo.odoo.service import model
# print 'test'
# _logger = logging.getLogger(__name__)
#
# PG_CONCURRENCY_ERRORS_TO_RETRY = (errorcodes.LOCK_NOT_AVAILABLE, errorcodes.SERIALIZATION_FAILURE, errorcodes.DEADLOCK_DETECTED)
# MAX_TRIES_ON_CONCURRENCY_FAILURE = 5
#
def check(f):
    @wraps(f)
    def wrapper(___dbname, *args, **kwargs):
        """ Wraps around OSV functions and normalises a few exceptions
        """
        dbname = ___dbname      # NOTE: this forbid to use "___dbname" as arguments in http routes

        def tr(src, ttype):
            # We try to do the same as the _(), but without the frame
            # inspection, since we aready are wrapping an osv function
            # trans_obj = self.get('ir.translation') cannot work yet :(
            ctx = {}
            if not kwargs:
                if args and isinstance(args[-1], dict):
                    ctx = args[-1]
            elif isinstance(kwargs, dict):
                if 'context' in kwargs:
                    ctx = kwargs['context']
                elif 'kwargs' in kwargs:
                    # http entry points such as call_kw()
                    ctx = kwargs['kwargs'].get('context')


            uid = 1
            if args and isinstance(args[0], (long, int)):
                uid = args[0]

            lang = ctx and ctx.get('lang')
            if not (lang or hasattr(src, '__call__')):
                return src

            # We open a *new* cursor here, one reason is that failed SQL
            # queries (as in IntegrityError) will invalidate the current one.
            cr = False

            if hasattr(src, '__call__'):
                # callable. We need to find the right parameters to call
                # the  orm._sql_message(self, cr, uid, ids, context) function,
                # or we skip..
                # our signature is f(registry, dbname [,uid, obj, method, args])
                try:
                    if args and len(args) > 1:
                        # TODO self doesn't exist, but was already wrong before (it was not a registry but just the object_service.
                        obj = self.get(args[1])
                        if len(args) > 3 and isinstance(args[3], (long, int, list)):
                            ids = args[3]
                        else:
                            ids = []
                    cr = odoo.sql_db.db_connect(dbname).cursor()
                    return src(obj, cr, uid, ids, context=(ctx or {}))
                except Exception:
                    pass
                finally:
                    if cr: cr.close()

                return False # so that the original SQL error will
                             # be returned, it is the best we have.

            try:
                cr = odoo.sql_db.db_connect(dbname).cursor()
                res = translate(cr, name=False, source_type=ttype,
                                lang=lang, source=src)
                if res:
                    return res
                else:
                    return src
            finally:
                if cr: cr.close()

        def _(src):
            return tr(src, 'code')

        tries = 0
        while True:
            try:
                if odoo.registry(dbname)._init and not odoo.tools.config['test_enable']:
                    raise odoo.exceptions.Warning('Currently, this database is not fully loaded and can not be used.')
                return f(dbname, *args, **kwargs)
            except (OperationalError, QWebException) as e:
                if isinstance(e, QWebException):
                    cause = e.qweb.get('cause')
                    if isinstance(cause, OperationalError):
                        e = cause
                    else:
                        raise
                # Automatically retry the typical transaction serialization errors
                if e.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise
                if tries >= MAX_TRIES_ON_CONCURRENCY_FAILURE:
                    _logger.info("%s, maximum number of tries reached" % errorcodes.lookup(e.pgcode))
                    raise
                wait_time = random.uniform(0.0, 2 ** tries)
                tries += 1
                _logger.info("%s, retry %d/%d in %.04f sec..." % (errorcodes.lookup(e.pgcode), tries, MAX_TRIES_ON_CONCURRENCY_FAILURE, wait_time))
                time.sleep(wait_time)
            except IntegrityError, inst:
                registry = odoo.registry(dbname)
                for key in registry._sql_error.keys():
                    if key in inst[0]:
                        raise ValidationError(tr(registry._sql_error[key], 'sql_constraint') or inst[0])
                if inst.pgcode in (errorcodes.NOT_NULL_VIOLATION, errorcodes.FOREIGN_KEY_VIOLATION, errorcodes.RESTRICT_VIOLATION):
                    msg = _('The operation cannot be completed, probably due to the following:\n- deletion: you may be trying to delete a record while other records still reference it\n- creation/update: a mandatory field is not correctly set')
                    _logger.debug("IntegrityError", exc_info=True)
                    try:
                        errortxt = inst.pgerror.replace('«','"').replace('»','"')
                        if '"public".' in errortxt:
                            context = errortxt.split('"public".')[1]
                            model_name = table = context.split('"')[1]
                        else:
                            last_quote_end = errortxt.rfind('"')
                            last_quote_begin = errortxt.rfind('"', 0, last_quote_end)
                            model_name = table = errortxt[last_quote_begin+1:last_quote_end].strip()
                        model = table.replace("_",".")
                        if model in registry:
                            model_obj = registry[model]
                            model_name = model_obj._description or model_obj._name
                        msg += _('\n\n[object with reference: %s - %s]') % (model_name, model)
                    except Exception:
                        pass
                    raise ValidationError(msg)
                else:
                    raise ValidationError(inst[0])

    return wrapper