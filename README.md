# Sift

An AI-powered centralized system for finding, parsing, and structuring insurer drug policy documents.

## Overview

Sift is a document intelligence pipeline built to simplify how drug coverage policies are discovered and analyzed across major health insurers. Instead of manually searching through scattered payer websites and long PDF policy files, Sift helps automate the process by locating relevant documents, extracting meaningful text, and converting the results into structured data.

The project is designed around a simple goal:

**Given a drug name, find the relevant insurer policy documents and turn them into usable, structured information.**

This makes it easier to compare policies, automate downstream workflows, and reduce the time spent navigating inconsistent insurer documentation.

## Problem

Drug and biologic coverage policies are often:

- spread across multiple insurer websites
- published in inconsistent formats
- difficult to search reliably
- buried in long PDF documents
- hard to compare across payers

Manual review is slow and error-prone. Sift addresses this by combining search, PDF processing, document classification, and structured extraction into one pipeline.

## Features

- Searches for policy documents related to a drug name
- Supports payer-focused retrieval workflows
- Downloads policy PDFs from insurer sources
- Extracts page-level text from documents
- Classifies document types to guide parsing strategy
- Selects the most relevant pages for extraction
- Structures extracted content into JSON/JSONL output
- Designed to scale to multiple insurers and multiple drugs

## Current Focus

Sift is currently focused on policy retrieval and extraction for large insurers such as:

- Cigna
- UnitedHealthcare (UHC)
- other major payers as support expands

The system is being developed to avoid hardcoding insurer-specific logic wherever possible, so search and extraction can be driven more by query design and reusable parsing logic.

## How It Works

The pipeline currently follows a workflow like this:

1. **User input**
   - A user provides a drug name

2. **Search**
   - Sift generates search queries to find relevant insurer policy documents

3. **Document retrieval**
   - Matching files, typically PDFs, are collected and downloaded

4. **PDF parsing**
   - Text is extracted page by page

5. **Document classification**
   - Each document is classified to determine its structure and expected content pattern

6. **Relevant page selection**
   - Sift identifies the pages most likely to contain useful policy details

7. **Structured extraction**
   - The extracted content is transformed into structured output for easier use downstream

## Project Goals

The main goals of Sift are:

- centralize payer policy retrieval
- reduce manual document review
- make policy data easier to search and compare
- build reusable tooling for healthcare policy intelligence
- create a scalable workflow for future insurer and document expansion

## Example Use Case

A user searches for a drug such as `Rituximab`.

Sift can then:

- search for matching insurer coverage policy documents
- retrieve likely policy PDFs
- extract the most relevant sections
- produce structured output summarizing what was found

This is much faster than manually searching payer websites and reading entire documents one by one.

## User Experience

Through the frontend, users can:

- search for a drug name
- retrieve relevant insurer policy documents
- review extracted policy content in one place
- compare findings without manually searching payer websites

## Developer Notes

Internally, Sift can store extracted results in structured formats such as JSON/JSONL to support downstream processing and analysis.

## Tech Direction

Sift sits at the intersection of:

- information retrieval
- document parsing
- PDF text extraction
- lightweight document classification
- structured data extraction
- healthcare policy automation

The long-term vision is to make policy information easier to discover, normalize, and use.

## Status

Sift is currently in active development.

Recent work has focused on:

- improving search reliability
- reducing redundant logic across parser and classifier workflows
- making the pipeline more modular
- improving extraction coverage for longer PDFs
- stabilizing structured output generation

## Challenges

Some current challenges include:

- inconsistent search results across insurer websites
- variability in PDF structure and formatting
- missing pages or incomplete extraction in some cases
- balancing payer-specific behavior with generalized logic
- ensuring structured output remains reliable across document types

These are active areas of improvement.

## Future Improvements

Planned improvements include:

- stronger retrieval across major insurers
- better handling of mixed-format policy documents
- improved page relevance ranking
- support for side-by-side payer comparison
- cleaner schema design for extracted policy information
- optional summarization and Q&A over extracted policies
- broader insurer coverage
- database scaling to ensure faster response time

## Why This Project Matters

Sift is meant to reduce friction in a workflow that is currently fragmented and time-consuming. By centralizing retrieval and automating extraction, it can help turn hard-to-use policy documents into something more accessible and actionable.

This project is especially useful as a foundation for:

- internal healthcare tooling
- policy comparison systems
- coverage research workflows
- AI-assisted document analysis pipelines
