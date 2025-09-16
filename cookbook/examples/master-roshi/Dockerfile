FROM ghcr.io/dowhiledev/nomos:latest
WORKDIR /app
COPY config.agent.yaml /app/config.agent.yaml
CMD ["nomos", "serve", "--config", "config.agent.yaml"]
