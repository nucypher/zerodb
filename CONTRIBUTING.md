# Introduction

### Welcome and thanks!

First off, thank you for considering contributing to ZeroDB. It's people like you that shape the future direction of the project and help to build the most secure database in existence. There's lot to do, from writing docs, to reviewing pull requests, to implementing ORAM. Every little bit counts and makes you a maintainer.

Following these guidelines helps to communicate that you respect the time of the developers managing and developing this open source project. In return, they should reciprocate that respect in addressing your issue, assessing changes, and helping you finalize your pull requests.

### What contributions are we looking for?

There are many ways to contribute, from writing tutorials or blog posts, improving the documentation, submitting bug reports and feature requests or writing code which can be incorporated into ZeroDB itself.

Please don't use the issue tracker for support questions. The [ZeroDB Slack channel](https://slack.zerodb.io/) is the best place to get help with your issue.

# Ground Rules
Responsibilities
* Ensure cross-platform compatibility for every change that's accepted. Windows, Mac, Debian & Ubuntu Linux.
* Create issues for any major changes and enhancements that you wish to make. Discuss things transparently and get community feedback.
* Keep feature versions as small as possible, preferably one new feature per version.
* Be welcoming to newcomers and encourage diverse new contributors from all backgrounds. See the [Python Community Code of Conduct](https://www.python.org/psf/codeofconduct/).

# Your First Contribution
Working on your first Pull Request? You can learn how from this *free* series, [How to Contribute to an Open Source Project on GitHub](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github).

At this point, you're ready to make your changes! Feel free to ask for help; everyone is a beginner at first :smile_cat:

If a maintainer asks you to "rebase" your PR, they're saying that a lot of code has changed, and that you need to update your branch so it's easier to merge.

# Getting started
By submitting a pull request, you are affirming that you've read, understood, and agree to the Developer's Certificate of Origin, DCO, below:

> Developer's Certificate of Origin 1.1
> 
> By making a contribution to this project, I certify that:
> 
> (a) The contribution was created in whole or in part by me and I
>     have the right to submit it under the open source license
>     indicated in the file; or
> 
> (b) The contribution is based upon previous work that, to the best
>     of my knowledge, is covered under an appropriate open source
>     license and I have the right under that license to submit that
>     work with modifications, whether created in whole or in part
>     by me, under the same open source license (unless I am
>     permitted to submit under a different license), as indicated
>     in the file; or

> (c) The contribution was provided directly to me by some other
>     person who certified (a), (b) or (c) and I have not modified
>     it.
> 
> (d) I understand and agree that this project and the contribution
>     are public and that a record of the contribution (including all
>     personal information I submit with it, including my sign-off) is
>     maintained indefinitely and may be redistributed consistent with
>     this project or the open source license(s) involved.


For something that is bigger than a one or two line fix:
1. Create your own fork of the code
2. Do the changes in your fork
3. If you like the change and think the project could use it:
  *Be sure you have followed the code style for the project.
  * Note the Developer's Certificate of Origin, DCO.
  * Note the Python Community Code of Conduct.
  * Send a pull request

Small contributions such as fixing spelling errors, where the content is small enough can be submitted by a contributor as a patch without creating a fork.

As a rule of thumb, changes are obvious fixes if they do not introduce any new functionality or creative thinking. As long as the change does not affect functionality, some likely examples include the following:
* Spelling / grammar fixes
* Typo correction, white space and formatting changes
* Comment clean up
* Bug fixes that change default return values or error codes stored in constants
* Adding logging messages or debugging output
* Changes to ‘metadata’ files like .gitignore, build scripts, etc.
* Moving source files from one directory or package to another

Some of the areas where we'd love to see contributions include:
* Detailed protocol spec (for implementing in other languages)
* Chrome extension
* Desktop end-to-end encrypted app kit (node.js + Python over Electron)
* Native Java zerodb -> .jar using Jython
* Native javascript over pypyjs
* JSON API wrapper for multiple languages
* More robust benchmarking
* Python Pandas/dataframe-like interface to the DB
* Optimize bulk-indexing of many records added at once
* SQL interface
* JDBC driver
* Proxy Re-Encryption for sharing
* Oblivious RAM for perfect security (hiding access patterns)
* Clustering / scalability (NEO storage, etc)
* Conflict resolution with partially homomorphic encryption

# How to report a bug
If you find a security vulnerability, do NOT open an issue. Email michael@zerodb.io instead.

Any security issues should be submitted directly to michael@zerodb.io
In order to determine whether you are dealing with a security issue, ask yourself these two questions:
* Can I access something that's not mine, or something I shouldn't have access to?
* Can I disable something for other people?

If the answer to either of those two questions are "yes", then you're probably dealing with a security issue. Note that even if you answer "no" to both questions, you may still be dealing with a security issue, so if you're unsure, just email us at michael@zerodb.io.

When filing an issue, make sure to answer these five questions:

1. What version of Python are you using?
2. What operating system and processor architecture are you using?
3. What did you do?
4. What did you expect to see?
5. What did you see instead?

General questions should go to the [ZeroDB Slack channel](https://slack.zerodb.io/) instead of the issue tracker.

If you find yourself wishing for a feature that doesn't exist in ZeroDB, let us know. There are bound to be others out there with similar needs. Many of the features that ZeroDB has today have been added because our users saw the need. Open an issue on our issues list on GitHub which describes the feature you would like to see, why you need it, and how it should work.

# Community
If there are other channels you use besides GitHub to discuss contributions, mention them here. You can also list the author, maintainers, and/or contributors here, or set expectations for response time.

You can chat with the core team on Slack(https://slack.zerodb.io/).
