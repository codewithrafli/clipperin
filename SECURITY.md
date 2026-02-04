# Security Policy

## Supported Versions
Currently, only the latest version of Clipperin is supported.

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not open a public issue**.

Instead, please send a private report:

1. **GitHub Security Advisory** (recommended)
   - Use GitHub's private vulnerability reporting feature
   - Navigate to "Security" → "Report a vulnerability"

2. **Email** (if GitHub is not available)
   - Send your report to: security@[your-repo].com
   - Include "SECURITY" in the subject line

**What to include:**
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact

**Response time:**
We will acknowledge your report within 48 hours and provide an estimate for when we expect to address it.

## Security Best Practices for Users

1. **Never share your API keys** - They should be stored in `.env` and never committed
2. **Review video sources** - Only process content from trusted sources
3. **Keep dependencies updated** - Run `pip install -U` regularly
4. **Run in isolated environment** - Consider using Docker or a dedicated VM
