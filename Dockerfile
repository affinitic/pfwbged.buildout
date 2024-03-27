FROM ubuntu:18.04

RUN apt-get -qy update && apt-get -o APT::Install-Recommends=false -qy install bash-completion curl htop less locales make ncurses-term software-properties-common telnet tzdata vim
RUN ln -sf /usr/share/zoneinfo/Europe/Brussels /etc/localtime
RUN echo "Europe/Brussels" > /etc/timezone; dpkg-reconfigure -f noninteractive tzdata

ENV PIP=9.0.3 \
    ZC_BUILDOUT=2.11.5 \
    SETUPTOOLS=38.7.0 \
    WHEEL=0.33.1 \
    PLONE_MAJOR=4 \
    PLONE_MINOR=4.3 \
    PLONE_VERSION=4.3.2

LABEL plone=$PLONE_VERSION \
    os="ubuntu" \
    os.version="18.04" \
    name="Buildout GED Parlement de la Fédération Wallonie-Bruxelles" \
    description="Plone image for PFWB GED" \
    maintainer="Affinitic"

RUN groupadd -g 209 plone \
 && useradd --system -m -d /plone -u 913 -g 209 plone \
 && mkdir -p /plone/ /data/filestorage /data/blobstorage /data/log /buildout-cache/download /buildout-cache/eggs

RUN apt-get update \
  && apt full-upgrade -y \
  && apt-get install -y --no-install-recommends \
    build-essential \
    cabextract \
    openjdk-8-jre \
    dpkg-dev \
    file \
    gcc \
    ghostscript \
    git \
    gosu \
    graphicsmagick \
    ldap-utils \
    libc6-dev \
    libjpeg-dev \
    libldap-2.4-2 \
    libldap2-dev \
    libmagic1 \
    libmemcached-dev \
    libmemcached11 \
    libpq-dev \
    libreadline-dev \
    libreoffice \
    libreoffice-java-common \
    libreoffice-script-provider-python \
    libsasl2-dev \
    libtiff5 \
    libtiff5-dev \
    libxml2 \
    libxml2-dev \
    libxslt1.1 \
    libxslt1-dev \
    links \
    lynx \
    multitail \
    netcat \
    openssh-client \
    poppler-utils \
    python \
    python-dev \
    python-pip \
    rsync \
    ruby \
    tidy \
    unrtf \
    wv \
  && curl -O http://archive.ubuntu.com/ubuntu/pool/universe/x/xlhtml/xlhtml_0.5.1-6ubuntu1_amd64.deb \
  && curl -O http://archive.ubuntu.com/ubuntu/pool/universe/x/xlhtml/ppthtml_0.5.1-6ubuntu1_amd64.deb \
  && dpkg -i xlhtml_0.5.1-6ubuntu1_amd64.deb ppthtml_0.5.1-6ubuntu1_amd64.deb \
  && rm xlhtml_0.5.1-6ubuntu1_amd64.deb ppthtml_0.5.1-6ubuntu1_amd64.deb


COPY *.cfg /plone/
WORKDIR /plone

RUN pip install setuptools==$SETUPTOOLS zc.buildout==$ZC_BUILDOUT wheel==$WHEEL \
 && buildout -c docker.cfg \
 && find /data  -not -user plone -exec chown plone:plone {} \+ \
 && find /plone -not -user plone -exec chown plone:plone {} \+ \
 && find /buildout-cache -not -user plone -exec chown plone:plone {} \+ \
 && rm -rf /Plone* \
 && rm -rf /var/lib/apt/lists/* \
 && rm -rf /buildout-cache/download/* \
 && rm -f /plone/.installed.cfg

RUN gem install docsplit \
  && ln -sf /usr/bin/virtualenv /usr/local/bin/virtualenv-2.7

USER plone
WORKDIR /plone

VOLUME /data/blobstorage
VOLUME /data/log

HEALTHCHECK --interval=1m --timeout=5s --start-period=1m \
  CMD nc -z -w5 127.0.0.1 8080 || exit 1

COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["start"]
