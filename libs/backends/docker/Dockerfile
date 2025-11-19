FROM python:3.11-slim

# Install common data science and utility packages
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    scipy \
    requests \
    pypdf \
    reportlab \
    pyyaml

# Create workspace structure
WORKDIR /workspace
RUN mkdir -p /workspace/data /workspace/scripts /workspace/results

# Create symlinks for clean paths
RUN ln -s /workspace/data /data && \
    ln -s /workspace/scripts /scripts && \
    ln -s /workspace/results /results

# Copy skills directory (static)
COPY skills/ /skills/

# Default command: keep container running
CMD ["sleep", "infinity"]

