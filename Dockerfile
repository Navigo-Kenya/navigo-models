# Headless Blender (4.2 LTS) for building the navigation models from code.
#   docker build -t navigo-blender .
FROM ubuntu:22.04

ARG BLENDER_VERSION=4.2.3
ARG BLENDER_SERIES=4.2

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl xz-utils \
      libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxext6 libxkbcommon0 \
      libsm6 libice6 libgl1 libegl1 libglu1-mesa \
 && rm -rf /var/lib/apt/lists/*

# The 350 MB archive is fetched with resume and retries (the mirror drops long downloads).
RUN url="https://download.blender.org/release/Blender${BLENDER_SERIES}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
 && for i in 1 2 3 4 5 6 7 8; do curl -fL --retry 5 --retry-all-errors -C - -s -o /tmp/blender.tar.xz "$url" && break; sleep 3; done \
 && xz -t /tmp/blender.tar.xz \
 && tar -xJf /tmp/blender.tar.xz -C /opt && rm /tmp/blender.tar.xz \
 && ln -s "/opt/blender-${BLENDER_VERSION}-linux-x64/blender" /usr/local/bin/blender

WORKDIR /work
ENTRYPOINT ["blender", "-b", "--factory-startup", "--python-exit-code", "1"]
