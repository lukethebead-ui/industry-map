import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import os

st.set_page_config(layout="wide", page_title="中国产业地图可视化系统")

# ===== 缓存数据加载 =====
# 把 load_basemap() 函数替换成下面这个：

@st.cache_data
def load_basemap():
    province = gpd.read_file("中国地图省.shp").to_crs(epsg=4326)
    nine_line = gpd.read_file("中国九段线.shp").to_crs(epsg=4326)
    beijing = gpd.read_file("北京市.shp", encoding='utf-8').to_crs(epsg=4326)
    shenzhen = gpd.read_file("深圳市.shp", encoding='utf-8').to_crs(epsg=4326)
    suzhou = gpd.read_file("苏州市.shp", encoding='utf-8').to_crs(epsg=4326)
    return province, nine_line, beijing, shenzhen, suzhou

@st.cache_data
def load_excel():
    return pd.read_excel("第四问python交互数据.xlsx")

@st.cache_data
def load_shp_safe(filepath):
    if os.path.exists(filepath):
        try:
            gdf = gpd.read_file(filepath)
            if gdf.crs is not None and str(gdf.crs).upper() != 'EPSG:4326':
                gdf = gdf.to_crs(epsg=4326)
            return gdf
        except:
            return None
    return None

province_gdf, nineline_gdf, beijing_gdf, shenzhen_gdf, suzhou_gdf = load_basemap()
df = load_excel()

# ===== 常量 =====
CITY_EN_MAP = {"北京": "BeiJing", "深圳": "ShenZhen", "苏州": "Suzhou"}
INDUSTRY_MAP = {"整体": 1, "第二产业": 2, "生产性服务业": 3, "生活性服务业": 4}
LISA_COLORS = {
    'HH': '#FF0000',    # 红色
    'HL': '#FF7F00',    # 橙色
    'LH': '#0000FF',    # 蓝色
    'LL': '#00FF00',    # 绿色
    '不显著': '#808080'  # 灰色
}

# ===== 侧边栏 =====
st.sidebar.header("🎛️ 产业类型选择")

def on_industry_change():
    st.session_state['map_key'] = st.session_state.get('map_key', 0) + 1

if 'map_key' not in st.session_state:
    st.session_state['map_key'] = 0
if 'current_industry' not in st.session_state:
    st.session_state['current_industry'] = "整体"

industry_choice = st.sidebar.selectbox(
    "选择产业类型",
    list(INDUSTRY_MAP.keys()),
    index=list(INDUSTRY_MAP.keys()).index(st.session_state['current_industry']),
    key='industry_selector',
    on_change=on_industry_change
)
st.session_state['current_industry'] = industry_choice
industry_code = INDUSTRY_MAP[industry_choice]

st.sidebar.markdown("---")
st.sidebar.markdown("""
**📖 LISA 聚类图例**
| 颜色 | 含义 |
|------|------|
| 🟥 | HH 高-高聚集 |
| 🟧 | HL 高-低聚集 |
| 🟦 | LH 低-高聚集 |
| 🟩 | LL 低-低聚集 |
| ⬜ | 不显著 |
""")

# ===== 大标题 =====
st.title("🏭 中国产业地图")
st.markdown(f"### 📍 {industry_choice} — 产业空间格局（北京·深圳·苏州）")

# ===== 构建地图 =====
m = folium.Map(
    location=[35.0, 105.0],
    zoom_start=5,
    tiles='CartoDB positron',
    control_scale=True
)

# ===== 1. 全国省面 + 九段线（不显示在图层控制里） =====
china_base = folium.FeatureGroup(control=False)

for _, row in province_gdf.iterrows():
    geom = row.geometry
    if geom.geom_type in ['Polygon', 'MultiPolygon']:
        centroid = geom.centroid
        name_text = str(row['name'])
        folium.GeoJson(
            geom.__geo_interface__,
            style_function=lambda x: {
                'fillColor': '#FFF8DC',
                'color': '#BBBBBB',
                'weight': 0.5,
                'fillOpacity': 1.0
            }
        ).add_to(china_base)
        folium.Marker(
            location=[centroid.y, centroid.x],
            icon=folium.DivIcon(
                html=f'<div style="font-size:12px;font-weight:bold;color:#333;background:rgba(255,255,255,0.6);padding:2px 6px;border-radius:3px;white-space:nowrap;">{name_text}</div>'
            )
        ).add_to(china_base)

folium.GeoJson(
    nineline_gdf,
    style_function=lambda x: {
        'color': '#FF0000',
        'weight': 2.0,
        'fillOpacity': 0,
        'dashArray': '5 5'
    }
).add_to(china_base)

china_base.add_to(m)

# ===== 2. 北京县区：边界 + 悬浮 + 地名标注 =====
bj_group = folium.FeatureGroup(name="北京市各区域划分", show=True)
for _, row in beijing_gdf.iterrows():
    geom = row.geometry
    if geom.geom_type in ['Polygon', 'MultiPolygon']:
        centroid = geom.centroid
        name_text = str(row['name'])
        # 画边界
        folium.GeoJson(
            geom.__geo_interface__,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': '#000000',
                'weight': 2.0,
                'fillOpacity': 0
            },
            tooltip=folium.Tooltip(name_text)
        ).add_to(bj_group)
        # 标注地名
        folium.Marker(
            location=[centroid.y, centroid.x],
            icon=folium.DivIcon(
                html=f'<div style="font-size:10px;font-weight:bold;color:#000;background:rgba(255,255,255,0.75);padding:1px 3px;border-radius:2px;white-space:nowrap;">{name_text}</div>'
            )
        ).add_to(bj_group)
bj_group.add_to(m)

# ===== 3. 深圳县区 =====
sz_group = folium.FeatureGroup(name="深圳市各区域划分", show=True)
for _, row in shenzhen_gdf.iterrows():
    geom = row.geometry
    if geom.geom_type in ['Polygon', 'MultiPolygon']:
        centroid = geom.centroid
        name_text = str(row['name'])
        folium.GeoJson(
            geom.__geo_interface__,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': '#000000',
                'weight': 2.0,
                'fillOpacity': 0
            },
            tooltip=folium.Tooltip(name_text)
        ).add_to(sz_group)
        folium.Marker(
            location=[centroid.y, centroid.x],
            icon=folium.DivIcon(
                html=f'<div style="font-size:10px;font-weight:bold;color:#000;background:rgba(255,255,255,0.75);padding:1px 3px;border-radius:2px;white-space:nowrap;">{name_text}</div>'
            )
        ).add_to(sz_group)
sz_group.add_to(m)

# ===== 4. 苏州县区 =====
su_group = folium.FeatureGroup(name="苏州市各区域划分", show=True)
for _, row in suzhou_gdf.iterrows():
    geom = row.geometry
    if geom.geom_type in ['Polygon', 'MultiPolygon']:
        centroid = geom.centroid
        name_text = str(row['name'])
        folium.GeoJson(
            geom.__geo_interface__,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': '#000000',
                'weight': 2.0,
                'fillOpacity': 0
            },
            tooltip=folium.Tooltip(name_text)
        ).add_to(su_group)
        folium.Marker(
            location=[centroid.y, centroid.x],
            icon=folium.DivIcon(
                html=f'<div style="font-size:10px;font-weight:bold;color:#000;background:rgba(255,255,255,0.75);padding:1px 3px;border-radius:2px;white-space:nowrap;">{name_text}</div>'
            )
        ).add_to(su_group)
su_group.add_to(m)


# ===== 遍历三个城市加载图层 =====
for city_cn, city_en in CITY_EN_MAP.items():
    lisa_gdf = load_shp_safe(f"{city_en} {industry_code} lisa.shp")
    if lisa_gdf is not None:
        folium.GeoJson(
            lisa_gdf,
            name=f"{city_cn} LISA聚类",
            style_function=lambda feat, colors=LISA_COLORS: {
                'fillColor': colors.get(feat['properties'].get('COType', ''), '#CCCCCC'),
                'color': '#333333',
                'weight': 0.5,
                'fillOpacity': 0.6
            }
        ).add_to(m)

    if industry_code != 1:
        sde_gdf = load_shp_safe(f"{city_en} {industry_code} SDE.shp")
        if sde_gdf is not None:
            folium.GeoJson(
                sde_gdf,
                name=f"{city_cn} 标准差椭圆",
                style_function=lambda x: {
                    'color': '#FF4500',
                    'weight': 2.5,
                    'fillColor': '#FF6347',
                    'fillOpacity': 0.15
                }
            ).add_to(m)

        center_gdf = load_shp_safe(f"{city_en} {industry_code} Center.shp")
        if center_gdf is not None:
            for _, row in center_gdf.iterrows():
                geom = row.geometry
                if geom.geom_type == 'Point':
                    lon, lat = geom.x, geom.y
                elif geom.geom_type == 'MultiPoint':
                    lon, lat = geom.geoms[0].x, geom.geoms[0].y
                else:
                    lon, lat = geom.centroid.x, geom.centroid.y
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(f"<b>{city_cn}</b> {industry_choice} 集聚中心", max_width=200),
                    icon=folium.Icon(color='red', icon='star', prefix='fa'),
                    name=f"{city_cn} 集聚中心",
                ).add_to(m)

# ===== 企业散点 =====
plot_df = df[df['行业具体分类'] == industry_choice] if industry_choice != "整体" else df
plot_df = plot_df.dropna(subset=['经度', '纬度'])

mc_alive = MarkerCluster(name="存活企业(蓝色)", options={'disableClusteringAtZoom': 16, 'maxClusterRadius': 80})
mc_dead = MarkerCluster(name="死亡企业(红色)", options={'disableClusteringAtZoom': 16, 'maxClusterRadius': 80})

for _, row in plot_df.iterrows():
    is_dead = row['企业生存状态(1=死亡，0=生存)'] == 1
    survival = "死亡" if is_dead else "存活"
    recruit = "有过招聘" if row['是否有招聘行为记录'] == 1 else "无招聘"

    popup = folium.Popup(f"""
    <div style="font-family:sans-serif;max-width:320px;font-size:12px;">
    <b>{str(row['企业名称'])[:25]}...</b>
    <hr style="margin:3px 0;">
    行业:{row['行业具体分类']}<br>
    注册资本:{row['注册资本(万元)']:.2f}万 | 年龄:{row['企业年龄']:.2f}年<br>
    状态:{survival} | 过往招聘状态:{recruit}<br>
    均薪:{row['平均历史薪资']:.0f} | 员工:{row['总招聘员工数']}<br>
    生存概率:{row['生存概率预测']:.4f}<br>
    文化:{row['企业文化标签']}<br>
    招聘次数:{row['海量招聘次数']}<br>
    企业所需技能:{str(row['核心技能需求'])[:60]}...<br>
    聚类:{row['点聚类归属']} | 核心圈:{row['核心圈归属']}
    </div>""", max_width=350)

    folium.CircleMarker(
        [row['纬度'], row['经度']],
        radius=3,
        color='#e74c3c' if is_dead else '#3498db',
        fill=True,
        fillOpacity=0.6,
        weight=0.5,
        popup=popup
    ).add_to(mc_dead if is_dead else mc_alive)

mc_alive.add_to(m)
mc_dead.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, width=1400, height=750, key=f"map_{st.session_state['map_key']}")

# ===== 底部统计 =====
st.markdown("---")
c1, c2, c3, c4, c5 = st.columns(5)
stat = plot_df
c1.metric("📊 企业总数", f"{len(stat):,}")
c2.metric("💀 死亡企业", f"{stat[stat['企业生存状态(1=死亡，0=生存)']==1].shape[0]:,}")
c3.metric("📝 有招聘", f"{stat[stat['是否有招聘行为记录']==1].shape[0]:,}")
c4.metric("🔴 HH聚集", f"{stat[stat['点聚类归属']=='HH'].shape[0]:,}")
c5.metric("⭕ 核心圈内", f"{stat[stat['核心圈归属']=='核心圈内'].shape[0]:,}")