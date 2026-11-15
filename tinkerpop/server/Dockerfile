# Gremlin Server 3.4.x + cypher-for-gremlin plugin, TinkerGraph loaded from GraphML
# native image (multi-arch Java 8 base): ~2x faster than tinkerpop/gremlin-server (amd64 only) on Apple Silicon
# build from the tinkerpop/ folder: docker build -f server/Dockerfile -t graphgenie-gremlin .
FROM eclipse-temurin:8-jre
ARG TINKERPOP_VERSION=3.4.13
RUN apt-get update && apt-get install -y --no-install-recommends unzip curl && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL https://archive.apache.org/dist/tinkerpop/${TINKERPOP_VERSION}/apache-tinkerpop-gremlin-server-${TINKERPOP_VERSION}-bin.zip -o /tmp/gs.zip \
 && unzip -q /tmp/gs.zip -d /opt && mv /opt/apache-tinkerpop-gremlin-server-${TINKERPOP_VERSION} /opt/gremlin-server && rm /tmp/gs.zip
WORKDIR /opt/gremlin-server
RUN bin/gremlin-server.sh install org.opencypher.gremlin cypher-gremlin-server-plugin 1.0.4
COPY server/gremlin-server-cypher.yaml conf/
COPY server/load-recommendations.groovy scripts/
COPY data/recommendations.graphml data/
EXPOSE 8182
CMD ["bin/gremlin-server.sh", "conf/gremlin-server-cypher.yaml"]
