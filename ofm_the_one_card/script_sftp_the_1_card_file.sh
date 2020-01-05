#!/bin/bash
HOST=sendfile.central.co.th
sftp_USERNAME=ofmfchftpprd
sftp_PASSWORD=2lG9Vn

local_folder=batch/
backup_folder=BKUP/
destination_folder=req/
local_path=/opt/media/ofm_the_one_card/
destination_path=/inbound/BCH_SBL_NRTSales/
temporary_path=/home/ubuntu/batch/

path_file_the1=$temporary_path$destination_folder

rm $path_file_the1*

cp $local_path$local_folder* $path_file_the1
cp $local_path$local_folder* $local_path$backup_folder

rm $local_path$local_folder*

export SSHPASS=$sftp_PASSWORD;
sshpass -e sftp -oBatchMode=no -b - $sftp_USERNAME@$HOST << !
   put -r $path_file_the1 $destination_path
   bye
!

rm $path_file_the1*
