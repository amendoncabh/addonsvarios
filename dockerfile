FROM odoo:10.0
MAINTAINER Papatpon D. <papatpon@trinityroots.co.th>

USER root
RUN set -x; apt-get update && apt-get install -y nano default-jdk
ENV TERM xterm

USER odoo
COPY odoo.conf /etc/odoo/odoo.conf
COPY ofm /mnt/extra-addons/ofm
COPY module_account_v10 /mnt/extra-addons/module_account_v10
COPY ofm/fonts/*.ttf /usr/share/fonts/truetype/

USER root
RUN chown -R odoo:odoo /mnt/*

# USER odoo