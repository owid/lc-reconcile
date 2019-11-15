# Our World in Data entity names reconciler

An [OpenRefine](https://openrefine.org/) reconciliation service for Our World in Data country names.

### Setup & usage

1. Install the requirements:
   ```
   pip install -r requirements.txt
   ```

2. Set the access credentials for your local Grapher database in `settings.cfg` (the Grapher MySQL database needs to be running)

3. Start the development server locally
   ```
   python reconcile.py
   ```

4. Download and install [**OpenRefine**](https://openrefine.org/download.html) on your machine.

5. Create an OpenRefine project with the CSV file of entities you need to reconcile (or use the example provided in `example.csv`).

OpenRefine project instructions:

1. **Create Project** → **Get data** from: **This Computer**. Then select the CSV file with country names. Click **Next**.
2. Click **Create Project** in the top right.
3. Click the **arrow** on the column name containing the country names → Edit column → Add column based on this column... New column name: `standardized_name`. Click **OK**.
4. Click the arrow on the newly created column → Reconcile → Start reconciling...
5. If you don't have the OWID service shown in the sidebar, click **Add Standard Service...** and then enter `http://0.0.0.0:5000/reconcile` as the URL (or whatever local URL the reconciler you set up earlier is running on)
6. Select **OWID Country Reconciliation Service** in the sidebar
7. Click **Start Reconciling** without changing anything
8. Wait for it to complete
9. Select **none** in the facets on the left to see which countries weren't matched.
   - Sometimes it's easy to see why the country names didn't match, e.g. they might be prefixed with "State of" or they might contain a suffix "former". Click on **Search for match** for each entity you think exists in the database but under a different name.
   - For entities you are not sure about, it's best to get in touch with the researchers.
   - **Some entities you might not be able to match.** That is OK. They can be inserted as brand new entities.
   - **You need to ensure you don't create any duplicates.**

10. After you are done trying to match the entities, click on **Reset All** to see all entities again.
11. Click on the arrow in the reconciled column and select **Edit column** → **Add column based on this column...**
12. Fill **New column name**: `db_entity_id`, **Expression**: `cell.recon.match.id`
13. Select **Export** (top right) → **Comma-separated value**
14. Use the CSV file in your importer.
