# Protótipo navegável do VAND: site estático servido por nginx.
#
# Imagem sem root: o nginx-unprivileged escuta na 8080 e roda como uid 101.
FROM nginxinc/nginx-unprivileged:1.27-alpine

LABEL org.opencontainers.image.title="VAND — protótipo navegável" \
      org.opencontainers.image.description="Alerta do INMET, registro de alagamento e trilha de estudo com material oficial." \
      org.opencontainers.image.source="https://github.com/JoseVitorGarcia/IA_VAND"

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY app/ /usr/share/nginx/html/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
