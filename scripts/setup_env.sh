#!/bin/bash
echo "🚀 Setting up DiscourseKG environment..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"

# Verify we're in the right place
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml not found in project root. Are you in the right directory?"
    exit 1
fi

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda not found. Please install Miniconda or Anaconda first."
    echo "   Download from: https://docs.conda.io/en/latest/miniconda.html"
    echo "   Then restart your terminal or run: source ~/.bashrc"
    exit 1
fi

# Set environment name
ENV_NAME="discoursekg"

# Parse command line arguments
FORCE_RECREATE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE_RECREATE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force]"
            echo "  --force, -f   : Force recreate environment"
            exit 1
            ;;
    esac
done

# Check if environment exists
echo "🔍 Checking for conda environment '$ENV_NAME'..."
if conda env list | grep -q "^$ENV_NAME\s"; then
    if [ "$FORCE_RECREATE" = true ]; then
        echo "🗑️  Removing existing environment (--force specified)..."
        conda env remove -n "$ENV_NAME" -y
    else
        echo "✅ Environment '$ENV_NAME' already exists"
        echo "   Use --force to recreate it"
    fi
fi

# Create environment if it doesn't exist
if ! conda env list | grep -q "^$ENV_NAME\s"; then
    echo "📦 Creating conda environment '$ENV_NAME' with Python 3.11..."
    if ! conda create -n "$ENV_NAME" python=3.11 -y; then
        echo "❌ Failed to create conda environment"
        exit 1
    fi
    echo "✅ Environment created successfully"
fi

# Activate the environment
echo "🔄 Activating environment '$ENV_NAME'..."
# Initialize conda for this shell session
eval "$(conda shell.bash hook)"
if ! conda activate "$ENV_NAME"; then
    echo "❌ Failed to activate conda environment"
    exit 1
fi

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install Jupyter and ipykernel FIRST (conda packages)
echo "🔮 Installing Jupyter and ipykernel..."
conda install -y jupyter ipykernel

# Install dependencies from pyproject.toml
echo "📚 Installing dependencies from pyproject.toml..."
if ! pip install -e .; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Install dev dependencies
echo "📚 Installing dev dependencies..."
if ! pip install -e ".[dev]"; then
    echo "⚠️  Warning: Failed to install dev dependencies, but main dependencies are installed"
fi

# Register Jupyter kernel
echo "🔮 Registering Jupyter kernel..."
python -m ipykernel install --user --name="$ENV_NAME" --display-name="DiscourseKG (Python 3.11)" --env PATH "$PATH" --env CONDA_DEFAULT_ENV "$ENV_NAME" --env CONDA_PREFIX "$CONDA_PREFIX"

echo ""
echo "🎉 Environment setup complete!"
echo "📁 Environment: $ENV_NAME"
echo "📍 Location: $CONDA_PREFIX"
echo ""
echo "📝 To activate the environment:"
echo "  conda activate $ENV_NAME"