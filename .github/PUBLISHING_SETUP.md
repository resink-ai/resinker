# Publishing Setup Guide

This guide explains how to set up your GitHub repository to automatically publish the `resinker` package to PyPI and TestPyPI when release tags are pushed.

## Prerequisites

1. **GitHub Repository Settings**: Make sure your repository has the following configured:

   - Actions are enabled
   - Workflow permissions allow reading and writing

2. **PyPI Accounts**: You need accounts on both:
   - [PyPI](https://pypi.org) (production)
   - [TestPyPI](https://test.pypi.org) (testing)

## GitHub Environment Configuration

The workflow uses GitHub Environments for secure publishing. You need to create two environments in your repository:

### 1. Create Environments

Go to your repository settings → Environments and create:

1. **Environment: `testpypi`**
   - No additional protection rules needed
2. **Environment: `pypi`**
   - Recommended: Add protection rules like required reviewers for production releases

### 2. Trusted Publishing (Recommended Method)

The workflow uses OpenID Connect (OIDC) for secure, keyless authentication with PyPI:

#### For TestPyPI:

1. Go to [TestPyPI](https://test.pypi.org/manage/account/publishing/)
2. Add a new "pending publisher" with:
   - **PyPI project name**: `resinker`
   - **Owner**: `your-github-username`
   - **Repository name**: `your-repo-name`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `testpypi`

#### For PyPI:

1. Go to [PyPI](https://pypi.org/manage/account/publishing/)
2. Add a new "pending publisher" with:
   - **PyPI project name**: `resinker`
   - **Owner**: `your-github-username`
   - **Repository name**: `your-repo-name`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`

## Alternative: API Token Method

If you prefer using API tokens instead of trusted publishing:

1. Generate API tokens:

   - [TestPyPI API Token](https://test.pypi.org/manage/account/token/)
   - [PyPI API Token](https://pypi.org/manage/account/token/)

2. Add them as environment secrets:

   - In `testpypi` environment: `PYPI_API_TOKEN`
   - In `pypi` environment: `PYPI_API_TOKEN`

3. Modify the workflow to use tokens (see commented alternative below).

## How to Trigger a Release

1. **Update the version** in `pyproject.toml`:

   ```toml
   version = "0.1.1"  # or whatever your new version is
   ```

2. **Create and push a release tag**:

   ```bash
   git tag release-0.1.1
   git push origin release-0.1.1
   ```

3. **Monitor the workflow**:
   - Go to your repository's Actions tab
   - Watch the "Publish to PyPI" workflow run
   - It will first publish to TestPyPI, then to PyPI

## Workflow Details

The workflow consists of three jobs:

1. **build**: Builds the package and validates it
2. **publish-to-testpypi**: Publishes to TestPyPI for testing
3. **publish-to-pypi**: Publishes to production PyPI (only after TestPyPI succeeds)

## Tag Pattern

The workflow triggers on tags matching the pattern `release-*`, such as:

- `release-0.1.0`
- `release-1.0.0`
- `release-2.1.3-beta`

## Troubleshooting

### Common Issues:

1. **"Package already exists"**: Make sure you've incremented the version in `pyproject.toml`
2. **"Authentication failed"**: Check your trusted publishing setup or API tokens
3. **"Environment not found"**: Make sure you've created the required environments in GitHub

### Checking Your Package:

After publishing to TestPyPI, you can test install your package:

```bash
pip install --index-url https://test.pypi.org/simple/ resinker
```

## Security Notes

- Never commit API tokens to your repository
- Use trusted publishing when possible (more secure than API tokens)
- Consider adding branch protection and required reviews for the `pypi` environment
