"""Stage 7: one chart of the two supplementary factors against on-time completion."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (the backend has to be chosen before pyplot is imported)
import seaborn as sns  # noqa: E402


def export_supplementary_chart(table, out_path):
    """Save box plots of prior publications and equipment share of the budget, by outcome.

    Args:
        table: one row per completed grant with on_time, prior_publications and share_equipment
        out_path: where the PNG is written
    """
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    panels = [("prior_publications", "Team publications in the last five years"),
              ("share_equipment", "Equipment share of the requested budget")]
    for axis, (column, label) in zip(axes, panels):
        sns.boxplot(x="on_time", y=column, hue="on_time", data=table, ax=axis, palette="Set2", legend=False)
        axis.set_title(f"{label}, by outcome (n = {len(table)} completed grants)")
        axis.set_xlabel("0 = extended, 1 = completed without extension")
        axis.set_ylabel(label)
    figure.tight_layout()
    figure.savefig(out_path, dpi=300)
    plt.close(figure)
