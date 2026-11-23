# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# --- builder: compile the wheel from source ---
FROM python:3.12.13-slim-trixie AS builder

ARG VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

RUN pip install uv --no-cache-dir

WORKDIR /src
COPY . .
RUN uv build --wheel --out-dir /dist


# --- siesta: the bundled siesta plugin, a static (musl) binary ---
# Same Rust version as plugins/siesta/rust-toolchain.toml.
FROM rust:1.97-alpine AS siesta

RUN apk add --no-cache musl-dev

WORKDIR /src
COPY clients/pyball-client-rs/Cargo.toml clients/pyball-client-rs/
COPY clients/pyball-client-rs/src clients/pyball-client-rs/src
COPY plugins/siesta/Cargo.toml plugins/siesta/Cargo.lock plugins/siesta/
COPY plugins/siesta/src plugins/siesta/src
RUN cd plugins/siesta && cargo build --release --locked


# --- activity: the bundled activity feed plugin, a static (musl) binary ---
# Same Rust version as plugins/activity/rust-toolchain.toml.
FROM rust:1.97-alpine AS activity

RUN apk add --no-cache musl-dev

WORKDIR /src
COPY clients/pyball-client-rs/Cargo.toml clients/pyball-client-rs/
COPY clients/pyball-client-rs/src clients/pyball-client-rs/src
COPY plugins/activity/Cargo.toml plugins/activity/Cargo.lock plugins/activity/
COPY plugins/activity/src plugins/activity/src
RUN cd plugins/activity && cargo build --release --locked

# --- base: shared system deps, locale, venv, unprivileged user ---
FROM python:3.12.13-slim-trixie AS base

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:${PATH} \
    HOME=/tmp

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install --no-install-recommends -y \
    locales \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    fonts-noto-core \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
    && localedef -i es_ES -c -f UTF-8 -A /usr/share/locale/locale.alias es_ES.UTF-8 \
    && groupadd -r pyballgroup && useradd -r -g pyballgroup pyballuser \
    && /usr/local/bin/python3 -m venv $VIRTUAL_ENV \
    && $VIRTUAL_ENV/bin/python3 -m pip install -U pip wheel \
    && fc-cache -f \
    && chown -R pyballuser:pyballgroup $VIRTUAL_ENV

# Bundled plugins go outside /pyball/plugins, which the workspace mounts over.
COPY --from=siesta /src/plugins/siesta/target/release/siesta /usr/local/bin/siesta
COPY --from=activity /src/plugins/activity/target/release/activity /usr/local/bin/activity

WORKDIR /builder
COPY --from=builder /dist/*.whl .


# --- telegram: Telegram + FastAPI topology ---
FROM base AS telegram

RUN WHEEL=$(ls /builder/*.whl) && \
    $VIRTUAL_ENV/bin/pip install --no-cache "${WHEEL}[telegram]" \
    && rm -rf /builder

WORKDIR /pyball
RUN chown -R pyballuser:pyballgroup /pyball

USER pyballuser
ENTRYPOINT ["pyball-telegram"]


# --- pyball: FastAPI topology, /signup opt-in via config (no Telegram) ---
FROM base AS pyball

RUN $VIRTUAL_ENV/bin/pip install --no-cache /builder/*.whl \
    && rm -rf /builder

WORKDIR /pyball
RUN chown -R pyballuser:pyballgroup /pyball

USER pyballuser
ENTRYPOINT ["pyball"]
