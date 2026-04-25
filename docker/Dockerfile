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

FROM python:3.12.13-slim-trixie AS builder

ARG VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

RUN pip install uv --no-cache-dir

WORKDIR /src
COPY . .
RUN uv build --wheel --out-dir /dist


FROM python:3.12.13-slim-trixie

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:${PATH}

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
    && chown -R pyballuser:pyballgroup $VIRTUAL_ENV

WORKDIR /builder
COPY --from=builder /dist/*.whl .

RUN $VIRTUAL_ENV/bin/python3 -m pip install --no-cache *.whl \
    && rm -rf /builder

WORKDIR /pyball
COPY static/ static/

RUN chown -R pyballuser:pyballgroup /pyball

USER pyballuser

ENTRYPOINT ["pyball"]
