#!/bin/sh
sleep 5 
mc alias set dockerminio http://minio:${MINIO_PORT} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} 

mc mb --ignore-existing dockerminio/blockscontent/temp/images/.keep
mc mb --ignore-existing dockerminio/blockscontent/temp/files/.keep
mc mb --ignore-existing dockerminio/blockscontent/images/.keep
mc mb --ignore-existing dockerminio/blockscontent/files/.keep

mc ilm import dockerminio/blockscontent < temp-lifecycle-config.json
mc ilm ls dockerminio/blockscontent
exit 0
