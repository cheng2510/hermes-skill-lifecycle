from setuptools import setup, find_packages

setup(
    name="hermes-skill-lifecycle",
    version="1.0.0",
    author="Hermes Team",
    author_email="hermes@example.com",
    description="Hermes Agent 技能生命周期管理系统",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/cheng2510/hermes-skill-lifecycle",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "flask>=2.3.0",
        "click>=8.1.0",
        "pyyaml>=6.0",
        "scikit-learn>=1.3.0",
        "python-Levenshtein>=0.21.0",
        "rich>=13.0.0",
        "tabulate>=0.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hermes-skills=src.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
