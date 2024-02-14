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

FROM python:3.10-slim as builder

ENV POETRY_VENV=/opt/poetry \
    PROD_VENV=/opt/venv

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && apt-get install -y git \
    # Poetry isolated virtual environment
    && /usr/local/bin/python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/python3 -m pip install -U pip wheel setuptools \
    && $POETRY_VENV/bin/python3 -m pip install poetry==1.7.1 poetry-dynamic-versioning \
    # Production virtual environment
    && /usr/local/bin/python3 -m venv $PROD_VENV \
    && $PROD_VENV/bin/python3 -m pip install -U pip wheel

WORKDIR /builder
COPY . .
RUN rm -rf dist/

RUN $POETRY_VENV/bin/poetry build --format wheel \
    && $PROD_VENV/bin/python3 -m pip install --no-cache dist/*.whl

#==========================
FROM python:3.10-alpine3.19

COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:${PATH}

WORKDIR /pyball
ENTRYPOINT ["pyball"]
