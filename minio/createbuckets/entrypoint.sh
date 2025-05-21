#!/bin/sh
sleep 5 
mc alias set dockerminio http://minio:${MINIO_PORT} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} 

mc mb --ignore-existing dockerminio/blockscontent

mc ilm import dockerminio/blockscontent < temp-lifecycle-config.json
mc ilm ls dockerminio/blockscontent

mc mb --ignore-existing dockerminio/react-app
mc anonymous set download dockerminio/react-app

mc mirror react-app/dist dockerminio/react-app/

exit 0
