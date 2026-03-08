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

FROM python:3.11-slim-bullseye AS builder

ARG PYBALL_COMPONENT

RUN apt-get update \
    && apt-get install -y git \
    && python3 -m pip install poetry poetry-dynamic-versioning

WORKDIR /package
COPY . .
WORKDIR $PYBALL_COMPONENT

RUN rm -rf dist/ \
    && poetry build -f wheel

FROM python:3.11-slim-bullseye

ARG UID
ARG USER
ARG PYBALL_COMPONENT

ENV PYBALL_COMPONENT=$PYBALL_COMPONENT
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:${PATH}

RUN useradd -u "${UID}" -m "${USER}" \
    && /usr/local/bin/python3 -m venv $VIRTUAL_ENV \
    && $VIRTUAL_ENV/bin/python3 -m pip install -U pip wheel \
    && apt-get update && apt-get install -y locales \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
    && localedef -i es_ES -c -f UTF-8 -A /usr/share/locale/locale.alias es_ES.UTF-8

COPY ./docker/entrypoint.bash /

WORKDIR /builder
COPY --from=builder /package/$PYBALL_COMPONENT/dist/*.whl .
RUN $VIRTUAL_ENV/bin/python3 -m pip install --no-cache *.whl \
    && rm -rf /builder

WORKDIR /pyball
VOLUME /pyball
ENTRYPOINT ["/entrypoint.bash"]
