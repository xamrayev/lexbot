FROM postgres:16-alpine

# minio-client provides `mc` for uploading dumps to the MinIO bucket
RUN apk add --no-cache minio-client

COPY backup.sh /backup.sh
RUN chmod +x /backup.sh

ENTRYPOINT ["/backup.sh"]
