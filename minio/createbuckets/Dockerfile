FROM --platform=linux/amd64 quay.io/minio/mc

COPY . .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
