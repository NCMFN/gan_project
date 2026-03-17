import matplotlib.pyplot as plt
import geopandas as gpd

plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300
})

world = gpd.read_file('https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip')
africa = world[world['CONTINENT'] == 'Africa']

fig, ax = plt.subplots(figsize=(10, 10))
africa.plot(ax=ax, color='lightgrey', edgecolor='black', linewidth=0.5)

ax.set_title("Map of Africa")
ax.axis('off')

plt.tight_layout()
plt.savefig("africa_map.png", bbox_inches='tight')
