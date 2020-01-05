#!/bin/sh
dir_odoo_interface='/opt/media/ofin_interface/'
dir_ofin_interface_ap='/home/ofin_user/AP/'
dir_ofin_interface_ar='/home/ofin_user/AR/'
dir_ofin_interface_gl='/home/ofin_user/GL/'
dir_ofin_interface_vendor='/home/ofin_user/VENDOR/'

for file in `find "${dir_odoo_interface}" -type f -name "H*.DAT"`
do
	mv $file $dir_ofin_interface_ap
done
for file in `find "${dir_odoo_interface}" -type f -name "H*.LOG"`
do
	mv $file $dir_ofin_interface_ap
done
for file in `find "${dir_odoo_interface}" -type f -name "L*.DAT"`
do
	mv $file $dir_ofin_interface_ap
done
for file in `find "${dir_odoo_interface}" -type f -name "L*.LOG"`
do
	mv $file $dir_ofin_interface_ap
done
for file in `find "${dir_odoo_interface}" -type f -name "PFSC*.VAL"`
do
	mv $file $dir_ofin_interface_ar
done
for file in `find "${dir_odoo_interface}" -type f -name "PFSC*.DAT"`
do
	mv $file $dir_ofin_interface_ar
done
for file in `find "${dir_odoo_interface}" -type f -name "ZXMINV*.VAL"`
do
	mv $file $dir_ofin_interface_gl
done
for file in `find "${dir_odoo_interface}" -type f -name "ZXMINV*.DAT"`
do
	mv $file $dir_ofin_interface_gl
done
for file in `find "${dir_odoo_interface}" -type f -name "S*.VAL"`
do
	mv $file $dir_ofin_interface_vendor
done
for file in `find "${dir_odoo_interface}" -type f -name "S*.DAT"`
do
	mv $file $dir_ofin_interface_vendor
done