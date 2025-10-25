.PHONY: setup

# Conda environment name
ENV_NAME = discoursekg

setup:
	@scripts/setup_env.sh --force