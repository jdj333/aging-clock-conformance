args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1) args[[1]] else "."
root <- normalizePath(root, mustWork = TRUE)
options(digits = 17)

expected_r <- "4.5.2"
expected_rpmm <- "1.25"
expected_cluster <- "2.1.8.1"
if (paste(R.version$major, R.version$minor, sep = ".") != expected_r) {
  stop(sprintf("Expected R %s, found %s", expected_r, R.version.string))
}

suppressPackageStartupMessages(library(RPMM))
if (as.character(packageVersion("RPMM")) != expected_rpmm) {
  stop(sprintf("Expected RPMM %s, found %s", expected_rpmm, packageVersion("RPMM")))
}
if (as.character(packageVersion("cluster")) != expected_cluster) {
  stop(sprintf("Expected cluster %s, found %s", expected_cluster, packageVersion("cluster")))
}

reference <- file.path(root, "data/reference/horvath-2013/original")
output <- file.path(root, "conformance/expected/r-4.5.2-rpmm-1.25")
dir.create(output, recursive = TRUE, showWarnings = FALSE)

printFlush <- function(value) {
  print(value)
  flush.console()
}

source(file.path(reference, "AdditionalFile24normalization.R"), chdir = FALSE)
probeAnnotation21kdatMethUsed <- read.csv(
  file.path(reference, "AdditionalFile22probeAnnotation21kdatMethUsed.csv"),
  stringsAsFactors = FALSE,
  check.names = FALSE
)
probeAnnotation27k <- read.csv(
  file.path(reference, "AdditionalFile21datMiniAnnotation27k.csv"),
  stringsAsFactors = FALSE,
  check.names = FALSE
)
datClock <- read.csv(
  file.path(reference, "AdditionalFile23predictor.csv"),
  stringsAsFactors = FALSE,
  check.names = FALSE
)
dat0 <- read.csv(
  file.path(reference, "AdditionalFile26MethylationDataExample55.csv"),
  stringsAsFactors = FALSE,
  check.names = FALSE
)

nSamples <- ncol(dat0) - 1
nProbes <- nrow(dat0)
stopifnot(nSamples == 16, nProbes == 27578)

XchromosomalCpGs <- as.character(probeAnnotation27k$Name[probeAnnotation27k$Chr == "X"])
selectXchromosome <- is.element(dat0[, 1], XchromosomalCpGs)
selectXchromosome[is.na(selectXchromosome)] <- FALSE
meanXchromosome <- rep(NA_real_, nSamples)
if (sum(selectXchromosome) >= 500) {
  meanXchromosome <- as.numeric(
    apply(as.matrix(dat0[selectXchromosome, -1]), 2, mean, na.rm = TRUE)
  )
}

match1 <- match(probeAnnotation21kdatMethUsed$Name, dat0[, 1])
if (sum(is.na(match1)) > 0) {
  stop(sprintf("%d normalization probes cannot be matched", sum(is.na(match1))))
}

dat1 <- dat0[match1, ]
asnumeric1 <- function(value) as.numeric(as.character(value))
dat1[, -1] <- apply(as.matrix(dat1[, -1]), 2, asnumeric1)
stopifnot(sum(is.na(dat1[, -1])) == 0)

trafo <- function(x, adult.age = 20) {
  x <- (x + 1) / (1 + adult.age)
  ifelse(x <= 1, log(x), x - 1)
}
anti.trafo <- function(x, adult.age = 20) {
  ifelse(x < 0, (1 + adult.age) * exp(x) - 1, (1 + adult.age) * x + adult.age)
}

set.seed(1)
normalizeData <- TRUE
source(file.path(reference, "AdditionalFile25stepwiseAnalysis.R"), chdir = FALSE)

published_two_significant_digits <- c(
  60.00, 43.00, 28.00, 38.00, 8.20, 20.00, 4.80, 38.00,
  6.80, 3.60, 31.00, 0.98, 62.00, 24.00, 8.00, 43.00
)
observed_two_significant_digits <- signif(datout$DNAmAge, 2)
if (!isTRUE(all.equal(observed_two_significant_digits, published_two_significant_digits, tolerance = 0))) {
  stop(
    paste(
      "Publisher age reproduction failed:",
      paste(observed_two_significant_digits, collapse = ", ")
    )
  )
}

linear_scores <- as.numeric(
  datClock$CoefficientTraining[[1]] +
    as.matrix(datMethClock) %*% as.numeric(datClock$CoefficientTraining[-1])
)
age_output <- data.frame(
  sample_id = datout$SampleID,
  linear_score = linear_scores,
  dnam_age_years = datout$DNAmAge,
  published_age_two_significant_digits = published_two_significant_digits,
  stringsAsFactors = FALSE
)
write.csv(
  age_output,
  file.path(output, "expected-ages.csv"),
  row.names = FALSE,
  quote = FALSE
)

normalized_clock <- data.frame(
  probe_id = colnames(datMethClock),
  t(as.matrix(datMethClock)),
  check.names = FALSE,
  stringsAsFactors = FALSE
)
write.csv(
  normalized_clock,
  file.path(output, "normalized-clock-probes.csv"),
  row.names = FALSE,
  quote = FALSE
)
writeLines(capture.output(sessionInfo()), file.path(output, "session-info.txt"))

cat(sprintf("Reproduced %d publisher tutorial ages at two significant digits.\n", nSamples))
