FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY . .
RUN go build -o /out/server ./cmd/server

FROM gcr.io/distroless/base-debian12:nonroot
COPY --from=build /out/server /server
EXPOSE 8080
USER nonroot:nonroot
CMD ["/server"]
