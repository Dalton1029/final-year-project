# Tableau Embedded

1. Open the running React dashboard and click **Download Tableau CSV** in the Tableau card. It is a live export from FastAPI, based on the current members, transactions and benefit ranking.
2. In Tableau Public, select **Create a Viz** and upload `benefitlens_tableau_data.csv`.
3. Build these views: `SUM(available_value)` by `member_name`, a stacked bar by `benefit_type`, and a priority table sorted by `relevance_score`.
4. Publish the Tableau workbook and copy its view URL.
5. Set `VITE_TABLEAU_VIEW_URL` to that URL in `frontend/.env`, then restart the React server. The published dashboard appears below the transaction form.

Use Tableau only with published data sources that do not expose card numbers or sensitive customer information.
