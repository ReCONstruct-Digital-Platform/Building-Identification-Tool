FROM python:3.11-slim-buster AS base

# Don't need this in container
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
#
ENV LANG=C.UTF-8
ENV IS_DOCKER_CONTAINER=True

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential git less curl wget ca-certificates \
        # geodjango
        gdal-bin binutils libproj-dev libgdal-dev \
        # postgresql
        libpq-dev postgresql-client \
    # utils
    vim \
    # cleanup
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
    && apt-get clean

# Install node and npm
ENV NVM_DIR=/usr/local/nvm
ENV NODE_VERSION=v22.13.0
RUN mkdir -p /usr/local/nvm
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
RUN /bin/bash -c "source $NVM_DIR/nvm.sh && nvm install $NODE_VERSION && nvm use --delete-prefix $NODE_VERSION"
ENV NODE_PATH=$NVM_DIR/versions/node/$NODE_VERSION/bin
ENV PATH=$NODE_PATH:$PATH
RUN node --version
RUN npm --version

# Set NPM environment variable
ENV NPM_BIN_PATH=$NODE_PATH

RUN mkdir /code
WORKDIR /code

# Create user first
RUN useradd -m app

# Copy requirements and install Python dependencies
COPY --chown=app:app requirements.txt manage.py /code/

RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt 
# Add debugpy for VSCode debugging
RUN python -m pip install debugpy

# Copy application code
COPY --chown=app:app buildings /code/buildings 
COPY --chown=app:app config /code/config 
COPY --chown=app:app static /code/static
COPY --chown=app:app assets /code/assets
COPY --chown=app:app templates /code/templates 
COPY --chown=app:app theme /code/theme
COPY --chown=app:app package.json /code/

RUN chown -R app:app /code

RUN if [ -f package.json ]; then npm install; fi

# Install theme dependencies
WORKDIR /code/theme/static_src
RUN npm install

# Return to code directory
WORKDIR /code

FROM base AS dev

# User is already set to app in base
# on linux
EXPOSE 8000
# Run dev server
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
# CMD ["bash"]


FROM base AS prod

# Install production server
USER root
RUN pip install gunicorn
USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
