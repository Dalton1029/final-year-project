# R analytics companion: run with Rscript r_analysis/benefit_analysis.R transactions.csv
args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0) stop("Provide a transactions CSV path")
transactions <- read.csv(args[1])
summary <- aggregate(amount ~ category, data = transactions, FUN = function(x) c(total=sum(x), average=mean(x)))
print(summary)
