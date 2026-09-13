# Bruker et lettvektig, offisielt Java-image i stedet for full Ubuntu
FROM openjdk:11-jre-slim

WORKDIR /valo

# Installer wget for å hente verktøyet, og rydd opp etterpå i samme lag
RUN apt-get update && \
    apt-get install -y wget && \
    wget -q https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar && \
    apt-get remove -y wget && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Kopier inn de nylig oppdaterte spesifikasjonsfilene (med de store konstantene)
COPY ValoStateMachine.tla .
COPY ValoStateMachine.cfg .

# -XX:+UseContainerSupport sørger for at Java adlyder minnegrensene du setter i skyen
# -workers auto gjør at TLC spiser alle tilgjengelige CPU-kjerner den får tildelt
ENTRYPOINT ["java", "-XX:+UseContainerSupport", "-XX:MaxRAMPercentage=80.0", "-cp", "tla2tools.jar", "tlc2.TLC", "-workers", "auto", "-config", "ValoStateMachine.cfg"]

# VIKTIG: Lagt til .tla til slutt så ikke TLC feiler ved oppstart
CMD ["ValoStateMachine.tla"]
