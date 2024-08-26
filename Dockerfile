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
    # cleanup
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
    && apt-get clean

RUN mkdir /code
COPY --chown=app:app requirements.txt manage.py /code/

WORKDIR /code

RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt 

RUN useradd -m app

COPY --chown=app:app buildings /code/buildings 
COPY --chown=app:app config /code/config 
COPY --chown=app:app templates /code/templates 
COPY --chown=app:app theme /code/theme



FROM base AS dev

USER app

# on linux
EXPOSE 8000
# Run dev server
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]


FROM base AS prod

# Install production server
RUN pip install gunicorn

USER app
EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
