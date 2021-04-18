FROM alpine

RUN apk add rsync

CMD ["sleep", "1000"]