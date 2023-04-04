FROM python:3.10-slim-buster
SHELL ["/bin/bash", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
	libgl1 libglib2.0-0 libsm6 libxrender1 libxext6\
	git\
    && rm -rf /var/lib/apt/lists/*

# Install requirements
COPY environment/requirements.txt .
ENV LANG=en_US.UTF-8 LANGUAGE=en_US:en #LC_ALL=en_US.UTF-8
RUN pip --no-cache-dir install nvidia-pyindex \
    && pip --no-cache-dir install -r requirements.txt

ENV MPLCONFIGDIR=/var/cache/matplotlib

# Install python package
COPY . /opt/bayesian-inference
WORKDIR /opt/bayesian-inference
RUN pip --no-cache-dir install -U . \
    && chmod o+rwx /root /opt/bayesian-inference \
    && mkdir -p /data \
    && chmod o+rwx -R /opt/bayesian-inference \
    && python /opt/bayesian-inference/bnn_inference/submodules/blitz/setup.py install
WORKDIR /data
ENTRYPOINT ["/opt/bayesian-inference/docker_entrypoint.sh"]
CMD ["/bin/bash"]
