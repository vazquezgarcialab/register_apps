FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive
RUN \
    # install packages dependencies
    apt-get update -yqq \
    && apt-get install -yqq \
        build-essential \
        cryptsetup \
        curl \
        dh-autoreconf \
        git \
        libarchive-dev \
        libglib2.0-dev \
        libseccomp-dev \
        locales \
        pkg-config \
        python-pip \
        python3-pip \
        python2.7 \
        python3.6 \
        runc \
        squashfs-tools \
        uuid-runtime \
        wget \
    && apt-get cleans

RUN \
    # configure locale, see https://github.com/rocker-org/rocker/issues/19
    && echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen \
    && locale-gen en_US.utf8 \
    && /usr/sbin/update-locale LANG=en_US.UTF-8

RUN \
    # Install Go
    export VERSION=1.19.5 OS=linux ARCH=amd64 \
    && wget -O /tmp/go${VERSION}.${OS}-${ARCH}.tar.gz \
        https://dl.google.com/go/go${VERSION}.${OS}-${ARCH}.tar.gz \
    && tar -C /usr/local -xzf /tmp/go${VERSION}.${OS}-${ARCH}.tar.gz && \
    && echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc \
    && source ~/.bashrc

RUN \
    # Install singularity
    SINGULARITY_VERSION=v3.10.5 \
    && SOURCE=/tmp/singularity_source \
    && git clone --recurse-submodules https://github.com/sylabs/singularity.git $SOURCE \
    && cd $SOURCE \
    && git checkout --recurse-submodules ${SINGULARITY_VERSION} \
    && ./mconfig \
    && make -C builddir \
    && sudo make -C builddir install \
    && rm -rf $SOURCE

# set locales
ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8

# mount the output volume as persistant
ENV OUTPUT_DIR /data
VOLUME ${OUTPUT_DIR}

# install register_apps
COPY . /code
RUN \
    pip3 install /code \
    && rm -rf /code \
    && /bin/bash -c "source /usr/local/bin/virtualenvwrapper.sh"

# add entry point
ENTRYPOINT ["register_toil"]
CMD ["--help"]

