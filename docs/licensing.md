# Licensing decisions

Project-created software and documentation use MIT. The bundled scientific
coefficients, publisher tutorial/scoring source, and normalized numerical derivatives
remain CC BY 2.0 with Steve Horvath's attribution. Upstream-written reference runner
and metadata retain the upstream MIT notice. [NOTICE.md](../NOTICE.md) identifies
the files, copyright holder, source revision, and transformations.

The publisher [rights notice](https://doi.org/10.1186/gb-2013-14-10-r115) and the
[pinned upstream NOTICE](https://github.com/jdj333/horvath_methylation_age/blob/c3d1cfe1beb162add6ce8c1a1c21606f89c8a64a/NOTICE.md)
were reviewed before import. Public accessibility alone was not used as a license.
The 2015 correction is linked for scientific context; its separate dataset is not
included. No personal sample or educational implementation lacking a reuse license
was copied. Dependencies are installed separately under their own licenses.

## Adding scientific artifacts

Record the author/publisher, exact URL/DOI, access date, license evidence, SHA-256,
and any transformation or parent artifact. A project software license does not grant
rights to redistribute data. If permission is unresolved, keep the artifact out of
the repository, represent its availability as unresolved, and provide only a lawful
obtain-and-verify workflow when justified. Such an artifact cannot silently become
a dependency of ordinary public CI.

Maintain an explicit allowlist when importing from mixed public/private repositories.
Retain third-party notices in the source tree, source distribution, and wheel. Never
rewrite scientific authorship, source rights, or original data under the project's MIT
notice. Exact licensing provenance is a review requirement for every new clock.
