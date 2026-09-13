FROM ubuntu:24.04

RUN apt-get update && apt-get install -y openjdk-11-jdk wget

WORKDIR /valo

RUN wget -q https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar

COPY ValoStateMachine.tla .
COPY ValoStateMachine.cfg .

ENTRYPOINT ["java", "-cp", "tla2tools.jar", "tlc2.TLC", "-config", "ValoStateMachine.cfg"]
CMD ["ValoStateMachine"]
