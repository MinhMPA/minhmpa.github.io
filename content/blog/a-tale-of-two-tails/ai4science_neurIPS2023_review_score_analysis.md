# AI4Science ICML2023 Accepted-Paper Review Score Analysis

This summary analyzes the public reviewer scores for accepted Oral and Poster presentations in the AI4Science workshop pages linked from OpenReview:

- Oral acceptances: https://openreview.net/group?id=NeurIPS.cc/2023/Workshop/AI4Science#tab-accept-oral
- Poster acceptances: https://openreview.net/group?id=NeurIPS.cc/2023/Workshop/AI4Science#tab-accept-poster

The data were retrieved from the OpenReview API v2 by querying accepted papers with `content.venue` equal to `NeurIPS2023-AI4Science Oral` or `NeurIPS2023-AI4Science Poster`. Reviewer scores were parsed from public `Official_Review` replies using the numeric prefix of `content.rating`, for example `7: Good paper, accept`.

## Summary Statistics

| Presentation type | Accepted papers | Public scored reviews | Papers with no public score | Mean review score | Median review score | Score range |
|---|---:|---:|---:|---:|---:|---:|
| Oral | 10 | 16 | 0 | 7.81 | 7.5 | 6-10 |
| Poster | 143 | 212 | 11 | 6.57 | 7.0 | 2-10 |

## Score Histogram

| Score | Oral count | Poster count |
|---:|---:|---:|
| 2 | 0 | 1 |
| 3 | 0 | 2 |
| 4 | 0 | 10 |
| 5 | 0 | 25 |
| 6 | 1 | 63 |
| 7 | 7 | 68 |
| 8 | 3 | 25 |
| 9 | 4 | 15 |
| 10 | 1 | 3 |

## Interpretation

The accepted Oral papers have a visibly higher score distribution than the accepted Poster papers. Among public scored reviews, 15 of 16 Oral scores are at least 7, and the lowest Oral score is 6. Poster scores cluster around 6 and 7, with 131 of 212 public scored reviews in those two bins.

The Poster group has a broader and lower-tailed distribution. There are 38 Poster scores at or below 5, while there are no Oral scores in that range. High scores are also more concentrated among Oral papers: scores of 8 or higher account for 8 of 16 Oral reviews, compared with 43 of 212 Poster reviews.

These results should be interpreted as an analysis of the public OpenReview review record, not necessarily the complete private reviewing record. Several papers have only one public scored review, and 11 accepted Poster papers have no public scored review exposed through the retrieved public API replies.

The full per-paper score table is in `ai4science_icml2023_review_scores.md` and `ai4science_icml2023_review_scores.csv`.
