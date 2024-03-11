FROM tooljet/tooljet:latest

# Generate the keys and store them in environment variables
RUN secret_key_base=$(openssl rand -hex 64)
RUN lockbox_master_key=$(openssl rand -hex 32)
ENV LOCKBOX_MASTER_KEY=lockbox_master_key
ENV SECRET_KEY_BASE=secret_key_base