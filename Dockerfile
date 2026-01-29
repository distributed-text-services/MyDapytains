FROM python:3.13.5-bookworm

RUN apt-get update && \
    apt-get -y --no-install-recommends install \
        curl \
        make \
        zsh \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Oh My Zsh (https://ohmyz.sh/)
RUN curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/70f0e5285f802ce6eb7feea4588ff8917246233e/tools/install.sh > install.sh
RUN echo "fbfcd1c0bf99acfcf77f7f999d75bb8c833d3b58643b603b3971d8cd1991fc2e install.sh" | sha256sum --check
RUN chmod +x install.sh && ./install.sh && rm install.sh

COPY . /app

WORKDIR /app

RUN make install

ENTRYPOINT exec make start
