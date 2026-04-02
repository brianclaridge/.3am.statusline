FROM ghcr.io/charmbracelet/vhs

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up a fake git repo at the demo project path
RUN mkdir -p /home/dev/acme-api \
    && cd /home/dev/acme-api \
    && git init \
    && git config user.email "dev@acme.io" \
    && git config user.name "Dev" \
    && git remote add origin https://github.com/acme-corp/acme-api.git \
    && echo "# acme-api" > README.md \
    && mkdir -p src/routes src/db src/middleware tests/integration deploy .claude/plans \
    && echo "module.exports = app" > src/routes/index.js \
    && git add -A \
    && git commit -m "initial commit" \
    && echo "change" >> README.md \
    && touch untracked.txt \
    && printf '# Add ANSI theme engine with 5 built-in palettes\n' > .claude/plans/bright-dancing-hopper.md \
    && printf '{"slug":"bright-dancing-hopper"}\n' > .transcript.jsonl

WORKDIR /statusline

# Copy project files
COPY pyproject.toml ./
COPY statusline.yml ./
COPY themes/ ./themes/
COPY src/ ./src/
COPY demo/ ./demo/

# Install deps into venv and set default theme
# Override padding to 0 for tight demo framing
RUN uv sync && .venv/bin/python src/set_theme.py default \
    && sed -i 's/^padding: 3/padding: 0/' statusline.yml

ENV STATUSLINE_DIR=/statusline

ENTRYPOINT ["vhs"]
CMD ["demo/demo.tape"]
