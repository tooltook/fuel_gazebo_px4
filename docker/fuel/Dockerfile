FROM local/ros-noetic-dev:latest

ARG NLOPT_VERSION=v2.7.1
USER root

RUN set -eux; \
    git clone --depth 1 --branch "${NLOPT_VERSION}" https://github.com/stevengj/nlopt.git /tmp/nlopt; \
    cmake -S /tmp/nlopt -B /tmp/nlopt/build \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
      -DBUILD_SHARED_LIBS=ON \
      -DNLOPT_PYTHON=OFF \
      -DNLOPT_GUILE=OFF \
      -DNLOPT_MATLAB=OFF \
      -DNLOPT_OCTAVE=OFF; \
    cmake --build /tmp/nlopt/build --parallel 2; \
    cmake --install /tmp/nlopt/build; \
    ldconfig; \
    rm -rf /tmp/nlopt

USER ros
WORKDIR /workspace
