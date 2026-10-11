SELECT withheld,label,COUNT(*) cases,AVG(spread) mean_spread,SUM(flips) eligibility_flips FROM observations GROUP BY withheld,label ORDER BY withheld,label;
SELECT label,COUNT(*) cases,MAX(spread) max_spread,AVG(n_outcomes) mean_outcomes FROM observations GROUP BY label ORDER BY label;
