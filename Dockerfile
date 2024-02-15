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

FROM python:3.11-slim-bullseye as builder

ENV POETRY_VENV=/opt/poetry

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && apt-get install -y git \
    && /usr/local/bin/python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/python3 -m pip install -U pip wheel setuptools \
    && $POETRY_VENV/bin/python3 -m pip install poetry==1.7.1 poetry-dynamic-versioning

WORKDIR /builder
COPY pyproject.toml poetry.lock README.md ./
COPY .git/ ./.git/
COPY pyball/ ./pyball/
RUN rm -rf dist/

RUN $POETRY_VENV/bin/poetry build --format wheel

#=======================
FROM python:3.11-slim-bullseye

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:${PATH}

WORKDIR /builder
COPY --from=builder /builder/dist/*.whl .

RUN echo "cython<3" > constraint.txt \
    && /usr/local/bin/python3 -m venv $VIRTUAL_ENV \
    && $VIRTUAL_ENV/bin/python3 -m pip install -U pip wheel \
    && PIP_CONSTRAINT=./constraint.txt \
        $VIRTUAL_ENV/bin/python3 -m pip install --no-cache *.whl \
    && apt-get update && apt-get install -y locales \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
    && localedef -i es_ES -c -f UTF-8 -A /usr/share/locale/locale.alias es_ES.UTF-8 \
    && rm -rf /builder
WORKDIR /pyball

ENTRYPOINT ["pyball"]

