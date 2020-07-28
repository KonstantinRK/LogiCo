from database_management import DBManager
from web_apis import PaperMeta
from string_processing import StringClassifier
import igraph
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from graph_colorings import *
sns.set(style="ticks", color_codes=True)
from pprint import pprint
import math
import statistics
from copy import deepcopy

class GraphAnalysis:

    def __init__(self, db, graph=None, *args, **kwargs):
        self.args = args
        self.kwars = kwargs
        self.db = db
        self.graph = None
        self.og_graph = None
        self._select_graph(graph, *args, **kwargs)
        self.visual_style = self.default_visual_style

    def _select_graph(self, graph, *args, **kwargs):
        if graph is not None:
            self.graph = graph
        else:
            self.graph = self.build_graph()
        self.og_graph = deepcopy(self.graph)

    def reset(self):
        self.graph = self.og_graph

    def build_graph(self):
        V, E, L, M = self.db.extract_citation_graph()
        graph = igraph.Graph(n=len(V), directed=True)
        for k, v in L.items():
            graph.vs[k] = v
        graph.add_edges(E)
        return graph

    def _persist(self, graph, persist):
        if persist:
            self.graph = graph
        else:
            return type(self)(self.db, graph, *self.args, **self.kwars)

    def isolated_vertices(self):
        return [v for v in self.graph.vs if self.graph.degree(v) == 0]

    def subgraph_non_isolated(self, persist=True):
        graph = self.graph.subgraph([v.index for v in self.graph.vs if self.graph.degree(v) != 0])
        return self._persist(graph, persist)

    def subgraph_values(self, values, attr="index", persist=True):
        if attr == "index":
            graph = self.graph.subgraph([v.index for v in self.graph.vs if v.index in values])
        else:
            graph = self.graph.subgraph([v.index for v in self.graph.vs if v[attr] in values])
        return self._persist(graph, persist)

    def get_vertex_by_key(self, key):
        return [v for v in self.graph.vs if v["key"] == key][0]

    def vs(self, pos):
        return self.graph.vs[pos]

    def default_visual_style(self, graph=None, vertex_color_foo=None, edge_color_foo=None, mode="in", vertex_size=None, layout="fr",
                             vertex_scale=0.4, edge_scale=0.0, elements=None, num_label=True, values=None, vertex_font_size=None,*args, **kwargs):
        if graph is None:
            graph = self.graph
        visual_style = {}
        if values is None:
            try:
                values = self.normalise_values(self.graph.strength(mode=mode, weights="weight"))
            except Exception:
                values = self.normalise_values(self.graph.strength(mode=mode))
        if vertex_size is None:
            visual_style["vertex_size"] = [5 + vertex_scale * values[i] for i in range(len(self.graph.vs))]
        else:
            visual_style["vertex_size"] = vertex_size
        if isinstance(vertex_color_foo, list):
            visual_style["vertex_color"] = vertex_color_foo
        elif vertex_color_foo is not None:
            visual_style["vertex_color"] = vertex_color_foo(*args, graph=graph, mode=mode, **kwargs)
        else:
            visual_style["vertex_color"] = "rgb(128, 159, 255)"
        # visual_style["vertex_label"] = g.vs["name"]
        visual_style["edge_width"] = 1
        visual_style["arrow_size"] = [0 for e in self.graph.es]
        visual_style["vertex_frame_width"] = 0
        visual_style["layout"] = graph.layout(layout)
        visual_style["bbox"] = (1920, 1080)
        visual_style["margin"] = 50
        if vertex_font_size is not None:
            visual_style["vertex_label_size"] = vertex_font_size
        if edge_color_foo is not None:
            if isinstance(edge_color_foo, list):
                visual_style["edge_color"] = edge_color_foo
            else:
                try:
                    visual_style["edge_color"] = edge_color_foo(graph, *args, **kwargs)
                except KeyError:
                    pass
        if elements is None:
            elements = []

        if num_label:
            val_dic = {x: elements.index(x) for x in elements}
            visual_style["vertex_label"] = [val_dic[v.index]+1 if v.index in elements else "" for v in graph.vs]
            for i in range(len(elements)):
                print(i, graph.vs[elements[i]]["name"])
        else:
            visual_style["vertex_label"] = [v["name"] if v.index in elements else "" for v in graph.vs]
        return visual_style

    def plot(self, visual_style=None, vertex_color=None, edge_color=None, path=None, undirected=True, mode="in", *args, **kwargs):
        if undirected:
            g = self.undirect_graph(persist=False).graph
        else:
            g = self.graph
        if visual_style is None:
            visual_style = self.default_visual_style(g, vertex_color, edge_color, mode=mode, *args, **kwargs)
        else:
            if not isinstance(visual_style, dict):
                visual_style = visual_style(g, vertex_color, edge_color, *args, **kwargs)

        if path is None:
            igraph.plot(g, **visual_style)
        else:
            igraph.plot(g, path, **visual_style)

    def undirect_graph(self, persist=True):
        g = deepcopy(self.graph)
        try:
            g.to_undirected(combine_edges={"weight": "sum"})
            g.es["weight"] = [int(i) for i in g.es["weight"]]
        except KeyError:
            pass
        return self._persist(g, persist=persist)

    def unloop_graph(self, persist=True):
        g = deepcopy(self.graph)
        try:
            g.simplify(multiple=False)
        except KeyError:
            pass
        return self._persist(g, persist=persist)

    def select_edges_by_weight(self, from_weight=None, to_weight=None, persist=True):
        graph = deepcopy(self.graph)
        if from_weight is not None:
            graph.delete_edges([(e.source, e.target) for e in graph.es if e["weight"] < from_weight])
        if to_weight is not None:
            graph.delete_edges([(e.source, e.target) for e in graph.es if e["weight"] > to_weight])
        return self._persist(graph, persist)


    @staticmethod
    def palette_value_density(values):
        dom_range = max(values)-min(values)+1
        pal = sns.color_palette("PuBu", dom_range)
        pal_map = {min(values)+i: pal[i] for i in range(dom_range)}
        return [pal_map[v] for v in values]

    def get_cycles(self):
        graph = deepcopy(self.graph)
        paths = []
        graph.vs["checked"] = False
        for x in self.graph.vs:
            v = x.index
            paths += self._get_cycle_from(graph, v, [])
        return paths

    @staticmethod
    def _get_cycle_from(graph, vertex, inp_path):
        if vertex in inp_path:
            return [inp_path + [vertex]]
        path = inp_path + [vertex]
        if len(path) > len(graph.vs):
            return [path]
        paths = []
        for n in graph.neighbors(path[-1], mode="out"):
            result = GraphAnalysis._get_cycle_from(graph, n, path)
            graph.vs[n]["checked"] = True
            if len(result) > 0:
                paths += result
        return paths

    def get_degree_distr(self, for_plot=False):
        max_val = max(self.graph.degree(mode="all"))
        degree = self.bin_list(self.graph.degree(mode="all"), max_val)
        in_degree = self.bin_list(self.graph.degree(mode="in"), max_val)
        out_degree = self.bin_list(self.graph.degree(mode="out"), max_val)
        if for_plot:
            data = [["all", k, degree[k]] for k in range(max_val+1)] +\
                   [["in", k, in_degree[k]] for k in range(max_val + 1)] +\
                   [["out", k, out_degree[k]] for k in range(max_val + 1)]
            data = pd.DataFrame(data, columns=["Type", "Degrees", "Vertex Count"])

        else:
            data = {"all": [degree[k] for k in range(max_val+1)],
                    "in": [in_degree[k] for k in range(max_val+1)],
                    "out": [out_degree[k] for k in range(max_val+1)]}
        data = pd.DataFrame(data)
        return data

    def plot_degree_distr(self, mode=None, drop_null=True, kind="line"):
        if mode is None:
            mode = ["all", "in", "out"]
        sns.set_style("whitegrid")
        if kind == "bar":
            data = self.get_degree_distr(for_plot=True)
            data = data[data["Type"].isin(mode)]
            if drop_null:
                data = data[data["Degrees"] != 0]
            ax = sns.barplot(x="Degrees", y="Vertex Count", hue="Type", data=data)
        elif kind == "line":
            data = self.get_degree_distr(for_plot=False)
            if drop_null:
                data = data.iloc[1:]
            ax = sns.lineplot(data=data)
        ax.get_title(loc="center")
        plt.tight_layout()
        ax.set_ylabel("Vertices")
        ax.set_xlabel("Degree")
        sns.despine(left=True)
        plt.show()


    def vertex_rankings(self, n=10, elements=None, attr=None, element_only=True, weight=None, as_dict=False):
        if elements is None:
            elements = ["degree", "in_degree", "out_degree",
                        "between", "closeness", "eigenvector", "pagerank"]
        if weight is not None:
            di_weight = [1/(1+ e) for e in weight]
        else:
            di_weight = None
        rankings = {
            "degree": self.top_x(self.graph.strength(mode="all", weights=weight), n=n, attr=attr, element_only=element_only),
            "in_degree": self.top_x(self.graph.strength(mode="in", weights=weight), n=n, attr=attr, element_only=element_only),
            "out_degree": self.top_x(self.graph.strength(mode="out", weights=weight), n=n, attr=attr, element_only=element_only),
            "between": self.top_x(self.graph.betweenness(weights=di_weight), n=n, attr=attr, element_only=element_only),
            "closeness": self.top_x(self.graph.closeness(weights=di_weight), n=n, attr=attr, element_only=element_only),
            "eigenvector": self.top_x(self.graph.evcent(weights=weight), n=n, attr=attr, element_only=element_only),
            "pagerank":  self.top_x(self.graph.pagerank(weights=weight), n=n, attr=attr, element_only=element_only),
        }
        rankings = {k: v for k, v in rankings.items() if k in elements}
        if not as_dict:
            df = pd.DataFrame(rankings)
            rankings = df[elements]

        return rankings

    def top_x(self, values, n=10, attr=None, val=None, element_only=True):
        if val is not None:
            n = len(values)
        if attr is None:
            result = sorted(zip(self.graph.vs, values), key=lambda x: x[1], reverse=True)[:n]
        elif attr == "index":
            result = sorted(zip([v.index for v in self.graph.vs], values), key=lambda x: x[1], reverse=True)[:n]
        elif isinstance(attr, list):
            result = sorted(zip([" ".join([str(x[i]) for i in attr]) for x in self.graph.vs], values), key=lambda x: x[1], reverse=True)[:n]
        else:
            result = sorted(zip(self.graph.vs[attr], values), key=lambda x: x[1], reverse=True)[:n]
        if val is not None:
            result = [i for i in result if i[1]>val]
        if element_only:
            result = [x[0] for x in result]
        return result

    def highlight_visual_style(self, graph=None, vertex_color_foo=None, edge_color_foo=None,
                               vertex_scale=0.4, edge_scale=0.4, elements=None, values=None, num_label=False):
        if graph is None:
            graph = self.graph
        if elements is None:
            elements = []
        visual_style = self.default_visual_style(graph, vertex_color_foo=vertex_color_foo,
                                                    edge_color_foo=edge_color_foo,
                                                    vertex_scale=vertex_scale, edge_scale=edge_scale)
        if values is not None:
            values = self.normalise_values(values)
            visual_style["vertex_size"] = [1 + vertex_scale * v for v in values]
            if elements is not None:
                color_out = "rgb(128, 159, 255)"
                color_in = "rgb(153, 0, 0)"
                visual_style["vertex_color"] = [color_in if graph.vs[i].index in elements else color_out
                                                for i in range(len(graph.vs))]
                # color_in = self.color_vertex(values, "Greens")
                # color_out = self.color_vertex(values)
                # visual_style["vertex_color"] = [color_in[i] if graph.vs[i].index in elements else color_out[i]
                #                                 for i in range(len(graph.vs))]
            else:
                visual_style["vertex_color"] = self.color_vertex(graph, values, "Greens")
        try:
            visual_style["edge_width"] = [1 + edge_scale * e["weight"] for e in self.graph.es]
        except KeyError:
            pass
        if num_label:
            val_dic = {x: elements.index(x) for x in elements}
            visual_style["vertex_label"] = [val_dic[v.index] if v.index in elements else "" for v in graph.vs]
            for i in range(len(elements)):
                print(i, graph.vs[elements[i]]["name"])
        else:
            visual_style["vertex_label"] = [v["name"] if v.index in elements else "" for v in graph.vs]
        return visual_style

    @staticmethod
    def normalise_values(values):
        max_val = max(values)
        if max_val > 0:
            return [i/max_val*100 for i in values]
        else:
            return values

    def print_vertex_rankings(self, n=10, elements=None, attr="name"):
        if elements is None:
            elements = ["degree", "in_degree", "out_degree", "eccentricity", "in_eccentricity", "out_eccentricity",
                        "between", "closeness", "eigenvector", "pagerank", "katz"]
        rankings = self.vertex_rankings(n, elements, as_dict=True)
        for k in elements:
            print(k, ": ")
            for x in rankings[k]:
                print("    ", round(x[1],4), x[0][attr])

    def graph_stats(self, as_dict=False, elements=None, weighted=False):
        if elements is None:
            elements = ["v_size", "e_size",
                        "min_degree", "max_degree", "avrg_degree", "median_degree",
                        "min_in_degree", "max_in_degree", "avrg_in_degree", "median_in_degree",
                        "min_out_degree", "max_out_degree", "avrg_out_degree", "median_out_degree",
                        "min_eccentricity", "max_eccentricity", "avrg_eccentricity", "median_eccentricity",
                        "min_in_eccentricity", "max_in_eccentricity", "avrg_in_eccentricity", "median_in_eccentricity",
                        "min_out_eccentricity", "max_out_eccentricity", "avrg_out_eccentricity", "median_out_eccentricity",
                        "radius", "diameter", "avrg_path_len", "connected", "density",
                        "clustering_coefficent", "vertex_connectivity", "edge_connectivity"]
        stats = {
            "v_size": self.num_vs(),
            "e_size": self.num_es(),
            "density": self.graph.density(),
            "radius": self.graph.radius(),
            "diameter": self.graph.diameter(),
            "avrg_path_len": self.graph.average_path_length(),
            "min_degree": min(self.graph.degree(mode="all")),
            "max_degree": max(self.graph.degree(mode="all")),
            "avrg_degree": statistics.mean(self.graph.degree(mode="all")),
            "median_degree": statistics.median(self.graph.degree(mode="all")),
            "min_in_degree": min(self.graph.degree(mode="in")),
            "max_in_degree": max(self.graph.degree(mode="in")),
            "avrg_in_degree": statistics.mean(self.graph.degree(mode="in")),
            "median_in_degree": statistics.median(self.graph.degree(mode="in")),
            "min_out_degree": min(self.graph.degree(mode="out")),
            "max_out_degree": max(self.graph.degree(mode="out")),
            "avrg_out_degree": statistics.mean(self.graph.degree(mode="out")),
            "median_out_degree": statistics.median(self.graph.degree(mode="out")),
            "min_eccentricity": min(self.graph.eccentricity()),
            "max_eccentricity": max(self.graph.eccentricity()),
            "avrg_eccentricity": statistics.mean(self.graph.eccentricity()),
            "median_eccentricity": statistics.median(self.graph.eccentricity()),
            "min_in_eccentricity": min(self.graph.eccentricity(mode="in")),
            "max_in_eccentricity": max(self.graph.eccentricity(mode="in")),
            "avrg_in_eccentricity": statistics.mean(self.graph.eccentricity(mode="in")),
            "median_in_eccentricity": statistics.median(self.graph.eccentricity(mode="in")),
            "min_out_eccentricity": min(self.graph.eccentricity(mode="out")),
            "max_out_eccentricity": max(self.graph.eccentricity(mode="out")),
            "avrg_out_eccentricity": statistics.mean(self.graph.eccentricity(mode="out")),
            "median_out_eccentricity": statistics.median(self.graph.eccentricity(mode="out")),
            "connected": self.graph.is_connected(),
            "clustering_coefficent": self.graph.transitivity_undirected(),
            "vertex_connectivity": self.graph.vertex_connectivity(),
            "edge_connectivity": self.graph.edge_connectivity()
        }
        if weighted:
            elements = elements + ["min_wdegree", "max_wdegree", "avrg_wdegree", "median_wdegree",
                        "min_in_wdegree", "max_in_wdegree", "avrg_in_wdegree", "median_in_wdegree",
                        "min_out_wdegree", "max_out_wdegree", "avrg_out_wdegree", "median_out_wdegree",]
            stats["min_wdegree"] = min(self.graph.strength(mode="all", weights="weight"))
            stats["max_wdegree"] = max(self.graph.strength(mode="all", weights="weight"))
            stats["avrg_wdegree"] = statistics.mean(self.graph.strength(mode="all", weights="weight"))
            stats["median_wdegree"] = statistics.median(self.graph.strength(mode="all", weights="weight"))
            stats["min_in_wdegree"] = min(self.graph.strength(mode="in", weights="weight"))
            stats["max_in_wdegree"] = max(self.graph.strength(mode="in", weights="weight"))
            stats["avrg_in_wdegree"] = statistics.mean(self.graph.strength(mode="in", weights="weight"))
            stats["median_in_wdegree"] = statistics.median(self.graph.strength(mode="in", weights="weight"))
            stats["min_out_wdegree"] = min(self.graph.strength(mode="out", weights="weight"))
            stats["max_out_wdegree"] = max(self.graph.strength(mode="out", weights="weight"))
            stats["avrg_out_wdegree"] = statistics.mean(self.graph.strength(mode="out", weights="weight"))
            stats["median_out_wdegree"] = statistics.median(self.graph.strength(mode="out", weights="weight"))

        if not as_dict:
            df = pd.DataFrame({k: [v] for k, v in stats.items()})
            stats = df[elements]
        return stats

    def print_graph_stats(self, elements=None):
        if elements is None:
            elements = ["v_size", "e_size",
                        "min_degree", "max_degree", "avrg_degree", "median_degree",
                        "min_in_degree", "max_in_degree", "avrg_in_degree", "median_in_degree",
                        "min_out_degree", "max_out_degree", "avrg_out_degree", "median_out_degree",
                        "min_eccentricity", "max_eccentricity", "avrg_eccentricity", "median_eccentricity",
                        "min_in_eccentricity", "max_in_eccentricity", "avrg_in_eccentricity", "median_in_eccentricity",
                        "min_out_eccentricity", "max_out_eccentricity", "avrg_out_eccentricity",
                        "median_out_eccentricity",
                        "radius", "diameter", "avrg_path_len", "connected", "density",
                        "clustering_coefficent", "vertex_connectivity", "edge_connectivity"]
        stats = self.graph_stats(True, elements=elements)
        for k in elements:
            print(k, ": ", stats[k])

    def num_vs(self):
        return len(self.graph.vs)

    def num_es(self):
        return len(self.graph.es)

    # def density(self):
    #     if self.graph.is_directed():
    #         return self.num_es() / (self.num_vs()*(self.num_vs()-1))
    #     else:
    #         return 2*self.num_es() / (self.num_vs() * (self.num_vs() - 1))

    @staticmethod
    def bin_list(inp_list, max_val=None):
        if max_val is None:
            max_val = max(inp_list)
        data = {k: 0 for k in range(max_val + 1)}
        for x in inp_list:
            data[x] += 1
        return data

    @staticmethod
    def color_edges(graph, *args, **kwargs):
        max_val = max(graph.es["weight"]) + 4
        min_val = min(graph.es["weight"])
        colors = sns.color_palette("Greys", max_val-min_val)
        color_dic = {min_val+i: colors[i] for i in range(len(colors))}
        return [color_dic[e["weight"]+3] for e in graph.es]

    @staticmethod
    def color_vertex_degree(graph, mode="in", colors="Blues", *args, **kwargs):
        max_val = max(graph.degree(mode=mode)) + 1
        min_val = min(graph.degree(mode=mode))
        colors = sns.color_palette(colors, max_val-min_val)
        color_dic = {min_val+i: colors[i] for i in range(len(colors))}
        return [color_dic[graph.degree(v, mode=mode)] for v in graph.vs]

    @staticmethod
    def color_vertex(values, colors="Blues", *args, **kwargs):
        max_val = max(values) + 1
        min_val = min(values)
        colors = sns.color_palette(colors, max_val-min_val)
        color_dic = {min_val+i: colors[i] for i in range(len(colors))}
        return [color_dic[v] for v in values]

    def subgraph_cluster(self, cluster, values, persist=True):
        graph = self.graph.subgraph([self.graph.vs[i] for i in range(len(values)) if values[i] == cluster])
        return self._persist(graph, persist)



class CitationGraphAnalysis(GraphAnalysis):

    def __init__(self, db, graph=None, *args, **kwargs):
        super().__init__(db, graph=graph, *args, **kwargs)

    def build_graph(self):
        V, E, L, M = self.db.extract_citation_graph()
        graph = igraph.Graph(n=len(V), directed=True)
        for k, v in L.items():
            graph.vs[k] = v
        graph.add_edges(E)
        return graph

    def subgraph_classified(self, persist=True):
        graph = self.graph.subgraph([v.index for v in self.graph.vs if "x" not in v["tags"]])
        return self._persist(graph, persist)

    def subgraph_fiber_elimination(self, persist=True, in_edges=1, out_edges=1, recursive=True):
        return self._persist(self._subgraph_fiber_elimination(self.graph, in_edges, out_edges, recursive), persist)

    @staticmethod
    def _subgraph_fiber_elimination(graph, in_edges=1, out_edges=1, recursive=True):
        subgraph = graph.subgraph([v.index for v in graph.vs
                                     if len(graph.neighbors(v, mode="out")) > out_edges or
                                     len(graph.neighbors(v, mode="in")) > in_edges])
        if recursive and len(subgraph.vs) != len(graph.vs):
            return CitationGraphAnalysis._subgraph_fiber_elimination(subgraph, in_edges, out_edges, recursive)
        else:
            return subgraph

    def subgraph_year(self, start_year=None, end_year=None, persist=True):
        graph = deepcopy(self.graph)
        if start_year is not None:
            graph = graph.subgraph([v.index for v in graph.vs if v["year"] >= start_year])
        if end_year is not None:
            graph = graph.subgraph([v.index for v in graph.vs if v["year"] <= end_year])
        return self._persist(graph, persist)

    def subgraph_relevant(self, persist=True):
        graph = self.graph.subgraph([v.index for v in self.graph.vs if v["relevant"]])
        return self._persist(graph, persist)

    def get_year_frequency(self, as_dict=False):
        stat = {}
        for v in self.graph.vs:
            if v["relevant"]:
                if stat.get(v["year"], None) is None:
                    stat[v["year"]] = 0
                stat[v["year"]] += 1
        if as_dict:
            return stat
        else:
            return pd.DataFrame(stat)

    def plot_year_frequency(self, start_year, end_year, frequency=1):
        data = self.get_year_frequency(as_dict=True)
        end_year = end_year+1
        sns.set_style("whitegrid")
        y = [0 if data.get(i, None) is None else data[i] for i in range(start_year, end_year)]
        ax = sns.barplot(x=list(range(start_year, end_year)),
                         y=y,
                         palette=self.palette_value_density(y))
                         #palette=sns.color_palette("PuBu", len(data.keys())))
        ax.get_title(loc="center")
        # ax.set_title('Publications per year')
        plt.tight_layout()
        ax.set_xticks(range(0, end_year-start_year, frequency))
        ax.set_xticklabels(range(start_year, end_year, frequency))
        ax.set_ylabel("Relevant Publications")
        ax.set_xlabel("Years")
        sns.despine(left=True)
        plt.show()

    def get_degree_by_year(self):
        data = {"year": [], "all": [], "in": [], "out": []}
        for y in range(2010, 2021):
            vs = [v.index for v in self.graph.vs if v["year"] == y]
            data["all"].append(statistics.mean(self.graph.degree(vs, mode="all")))
            data["in"].append(statistics.mean(self.graph.degree(vs, mode="in")))
            data["out"].append(statistics.mean(self.graph.degree(vs, mode="out")))
            data["year"].append(y)
        df = pd.DataFrame(data)
        df = df.set_index("year")
        print(df)
        return df


    def plot_degree_by_year(self):
        sns.set_style("whitegrid")
        data = self.get_degree_by_year()
        data = data[["all", "in", "out"]]

        ax = sns.lineplot(data=data)
        ax.get_title(loc="center")
        plt.tight_layout()
        ax.set_ylabel("Average Degree")
        ax.set_xlabel("Year")
        sns.despine(left=True)
        plt.show()

    def get_relevant_frequency(self, as_dict=False):
        tags = ["0", "1", "2", "-1", "-1+1", "-2", "-2+1"]
        translation = {"0": "0", "1": "-1", "2": "-2", "-1": "+1", "-1+1": "+1-1", "-2": "+2", "-2+1": "+2-1"}
        dic = {"relevant": {k: 0 for k in tags}, "not_relevant": {k: 0 for k in tags}}
        for v in self.graph.vs:
            check = [1 if k in v["tags"] else 0 for k in tags]
            for i in range(len(tags)):
                if check[i] == 1:
                    if v["relevant"]:
                        dic["relevant"][tags[i]] += 1
                    else:
                        dic["not_relevant"][tags[i]] += 1
                    break
        if as_dict:
            return dic
        data = []
        for relevant in ["relevant", "not_relevant"]:
            for index in tags:
                if relevant == "relevant":
                    value = dic[relevant][index]
                    data.append([translation[index], relevant.capitalize(), value])
                else:
                    data.append([translation[index], "Total", dic["relevant"][index] + dic["not_relevant"][index]])

        df = pd.DataFrame(data, columns=["Step", "Legend", "Publications"])
        return df

    def plot_relevant_frequency(self):
        data = self.get_relevant_frequency()
        sns.set_style("whitegrid")
        sns.barplot(x="Step", y="Publications", hue="Legend", data=data, palette=sns.color_palette("PuBu_r", 2))
        sns.despine(left=True)
        plt.show()

    @staticmethod
    def color_relevance(graph, *args, **kwargs):
        color = []
        for v in graph.vs:
            if not v["relevant"]:
                if "0" in v["tags"]:
                    color.append("rgb(0, 51, 204)")
                else:
                    color.append("rgb(128, 159, 255)")
            else:
                if "0" in v["tags"]:
                    color.append("rgb(153, 0, 0)")
                else:
                    color.append("rgb(255, 102, 102)")
        return color

    @staticmethod
    def color_relevance_and_steps(graph, *args, **kwargs):
        color = []
        for v in graph.vs:
            if v["relevant"]:
                if "0" in v["tags"]:
                    color.append("rgb(112, 219, 112)")
                elif "1" in v["tags"]:
                    color.append("rgb(255, 102, 102)")
                elif "2" in v["tags"]:
                    color.append("rgb(255, 179, 179)")
                elif "-1" in v["tags"]:
                    color.append("rgb(204, 0, 0)")
                elif "-2" in v["tags"]:
                    color.append("rgb(153, 0, 0)")
                elif "-1+1" in v["tags"]:
                    color.append("rgb(204, 0, 0)")
                elif "-2+1" in v["tags"]:
                    color.append("rgb(153, 0, 0)")
                else:
                    color.append("rgb(0, 0, 0)")
                    print(v["key"], v["name"], v["tags"])
            elif not v["relevant"]:
                if "0" in v["tags"]:
                    color.append("rgb(112, 219, 112)")
                elif "1" in v["tags"]:
                    color.append("rgb(193, 208, 240)")
                elif "2" in v["tags"]:
                    color.append("rgb(111, 146, 220)")
                elif "-1" in v["tags"]:
                    color.append("rgb(50, 99, 205)")
                elif "-2" in v["tags"]:
                    color.append("rgb(35, 69, 144)")
                elif "-1+1" in v["tags"]:
                    color.append("rgb(50, 99, 205)")
                elif "-2+1" in v["tags"]:
                    color.append("rgb(35, 69, 144)")
                else:
                    color.append("rgb(0, 0, 0)")
                    print(v["key"], v["name"], v["tags"])
            else:
                color.append("rgb(0, 0, 0)")
                print(v["key"], v["name"], v["tags"])
        return color

    @staticmethod
    def color_steps(graph, *args, **kwargs):
        color = []
        for v in graph.vs:
            if "0" in v["tags"]:
                color.append("rgb(204, 0, 0)")
            elif "1" in v["tags"]:
                color.append("rgb(77, 121, 255)")
            elif "2" in v["tags"]:
                color.append("rgb(179, 198, 255)")
            elif "-1" in v["tags"]:
                color.append("rgb(30, 123, 30)")
            elif "-2" in v["tags"]:
                color.append("rgb(111, 220, 111)")
            elif "-1+1" in v["tags"]:
                color.append("rgb(115, 0, 230)")
            elif "-2+1" in v["tags"]:
                color.append("rgb(179, 102, 255)")
            else:
                color.append("rgb(0, 0, 0)")
                print(v["key"], v["name"], v["tags"])
        return color

    def default_visual_style(self, graph=None, vertex_color_foo=None, edge_color_foo=None, mode="in", vertex_size=None,
                                 layout="fr", vertex_scale=0.4, edge_scale=0.4, vertex_label=False, *args, **kwargs):
        if graph is None:
            graph = self.graph
        avr_in = sorted(self.graph.degree(mode=mode), reverse=True)[min(len(self.graph.vs)-1,10)]
        visual_style = super().default_visual_style(graph=graph, layout=layout,
                                                    vertex_color_foo=vertex_color_foo,
                                                    edge_color_foo= edge_color_foo,
                                                    mode=mode, vertex_scale=vertex_scale,
                                                    vertex_size=vertex_size,
                                                    edge_scale=edge_scale, *args, **kwargs)
        if vertex_label:
            visual_style["vertex_label"] = [v["name"] if self.graph.degree(v, mode=mode) > avr_in else "" for v in graph.vs]
        elif isinstance(vertex_label, list):
            visual_style["vertex_label"] = vertex_label
        return visual_style


class AuthorGraphAnalysis(GraphAnalysis):

    def __init__(self, db, graph=None, papers=None, multiple_edges=False, *args, **kwargs):
        self.papers = papers
        self.multiple_edges = multiple_edges
        super().__init__(db, graph=graph, *args, **kwargs)

    def merge_with_collab_graph(self, collab_graph, addi_weight_scaling=0, multi_weight_scaling=1, persist=True, edgs_ids=False):
        graph = deepcopy(self.graph)
        collab_graph = deepcopy(collab_graph)
        if not collab_graph.is_directed():
            collab_graph.to_directed()
        edges = []
        for e in collab_graph.es:
            v, w = e.tuple
            eid = graph.get_eid(v, w, error=False)
            # print("#"*100)
            # print(graph.vs[v]["name"], "-->", graph.vs[w]["name"], "|", collab_graph.vs[v]["name"], "-->", collab_graph.vs[w]["name"])
            if eid == -1:
                # print("NEW")
                graph.add_edges([(v,w)])
                eid = graph.get_eid(v, w, error=False)
                graph.es[eid]["weight"] = e["weight"]*multi_weight_scaling + addi_weight_scaling
                graph.es[eid]["paper_to"] = e["paper"]
                graph.es[eid]["paper_from"] = e["paper"]
            else:
                # print("EXISTING")
                # print(graph.es[eid]["weight"])
                # print([p["name"] for p in graph.es[eid]["paper_from"]])
                # print([p["name"] for p in graph.es[eid]["paper_to"]])
                graph.es[eid]["weight"] += e["weight"]*multi_weight_scaling + addi_weight_scaling
                graph.es[eid]["paper_to"] += e["paper"]
                graph.es[eid]["paper_from"] += e["paper"]
            edges.append((graph.vs[v]["key"], graph.vs[w]["key"]))
            # print("-"*100)
            # print(graph.es[eid]["weight"])
            # print([p["name"] for p in graph.es[eid]["paper_from"]])
            # print([p["name"] for p in graph.es[eid]["paper_to"]])
            # print("")

        if edgs_ids:
            return self._persist(graph, persist), edges
        else:
            return self._persist(graph, persist)


    @staticmethod
    def color_edges(graph, *args, **kwargs):
        max_val = max(graph.es["weight"]) + 1
        min_val = min(graph.es["weight"])
        colors = sns.color_palette("PuBu", max_val-min_val)
        color_dic = {min_val+i: colors[i] for i in range(len(colors))}
        return [color_dic[e["weight"]] for e in graph.es]

    def default_visual_style(self, graph=None, vertex_color_foo=None, edge_color_foo=None, mode="in", vertex_size=None,
                             layout="fr", vertex_scale=0.4, edge_scale=0.4, *args, **kwargs):
        if graph is None:
            graph = self.graph
        avr_in = sorted(self.graph.degree(mode=mode), reverse=True)[min(len(self.graph.vs)-1,20)]
        visual_style = super().default_visual_style(graph=graph, layout=layout,
                                                    vertex_color_foo=vertex_color_foo,
                                                    edge_color_foo= edge_color_foo,
                                                    mode=mode, vertex_scale=vertex_scale,
                                                    vertex_size=vertex_size,
                                                    edge_scale=edge_scale, *args, **kwargs)
        visual_style["edge_width"] = [1 + edge_scale*e["weight"] for e in self.graph.es]
        # visual_style["vertex_label"] = [v["name"] if self.graph.degree(v, mode=mode) >= avr_in else "" for v in graph.vs]
        # visual_style["vertex_label"] = [v["name"] if self.graph.degree(v, mode=mode) > avr_in else "" for v in graph.vs]
        # visual_style["vertex_label"] = graph.vs["name"]
        return visual_style

    def highlight_visual_style(self, graph=None, vertex_color_foo=None, edge_color_foo=None, vertex_size=None,
                             vertex_scale=0.4, edge_scale=0.4, elements=None, values=None, num_label=False):
        if graph is None:
            graph = self.graph
        if elements is None:
            elements = []
        visual_style = super().default_visual_style(graph=graph,
                                                    vertex_color_foo=vertex_color_foo,
                                                    edge_color_foo= edge_color_foo,
                                                    vertex_scale=vertex_scale,
                                                    vertex_size=vertex_size,
                                                    edge_scale=edge_scale)
        if values is not None:
            values = self.normalise_values(values)
            visual_style["vertex_size"] = [1+vertex_scale*v for v in values]
            if elements is not None:
                color_out = "rgb(128, 159, 255)"
                color_in = "rgb(153, 0, 0)"
                visual_style["vertex_color"] = [color_in if graph.vs[i].index in elements else color_out
                                                for i in range(len(graph.vs))]
                # color_in = self.color_vertex(values, "Greens")
                # color_out = self.color_vertex(values)
                # visual_style["vertex_color"] = [color_in[i] if graph.vs[i].index in elements else color_out[i]
                #                                 for i in range(len(graph.vs))]
            else:
                visual_style["vertex_color"] = self.color_vertex(graph, values, "Greens")

        visual_style["edge_width"] = [1 + edge_scale*e["weight"] for e in self.graph.es]
        if num_label:
            val_dic = {x: elements.index(x) for x in elements}
            visual_style["vertex_label"] = [val_dic[v.index] if v.index in elements else "" for v in graph.vs]
            for i in range(len(elements)):
                print(i, graph.vs[elements[i]]["name"])
        else:
            visual_style["vertex_label"] = [v["name"] if v.index in elements else "" for v in graph.vs]
        return visual_style

    def build_graph(self):
        V, E, L, M = self.db.extract_author_graph(papers=self.papers, multiple_edges=self.multiple_edges)
        graph = igraph.Graph(n=len(V), directed=True)
        for k, v in L.items():
            graph.vs[k] = v
        graph.add_edges(E)
        for k, v in M.items():
            graph.es[k] = v
        return graph

    @staticmethod
    def color_vertex_pub(graph, colors="Blues", *args, **kwargs):
        pubs = [len(v["papers"]) for v in graph.vs]
        max_val = max(pubs) + 1
        min_val = min(pubs)
        colors = sns.color_palette(colors, max_val-min_val)
        color_dic = {min_val+i: colors[i] for i in range(len(colors))}
        return [color_dic[p] for p in pubs]

    def vertex_rankings(self, n=10, elements=None, attr=None, element_only=True, weight=None, as_dict=False, papers=0):
        if elements is None:
            elements = ["degree", "in_degree", "out_degree",
                        "between", "closeness", "eigenvector", "pagerank", "num_pub"]
        if weight is not None:
            di_weight = [1 / (1 + e) for e in weight]
        else:
            di_weight = None
        rankings = {
            "degree": self.top_x(self.graph.strength(mode="all", weights=weight), n=n, attr=attr,
                                 element_only=element_only),
            "in_degree": self.top_x(self.graph.strength(mode="in", weights=weight), n=n, attr=attr,
                                    element_only=element_only),
            "out_degree": self.top_x(self.graph.strength(mode="out", weights=weight), n=n, attr=attr,
                                     element_only=element_only),
            "between": self.top_x(self.graph.betweenness(weights=di_weight), n=n, attr=attr, element_only=element_only),
            "closeness": self.top_x(self.graph.closeness(weights=di_weight), n=n, attr=attr, element_only=element_only),
            "eigenvector": self.top_x(self.graph.evcent(weights=weight), n=n, attr=attr, element_only=element_only),
            "pagerank": self.top_x(self.graph.pagerank(weights=weight), n=n, attr=attr, element_only=element_only),
            "num_pub": self.top_x([len([p for p in v["papers"] if p in papers]) for v in self.graph.vs], n=n, attr=attr, element_only=element_only),
        }
        rankings = {k: v for k, v in rankings.items() if k in elements}
        if not as_dict:
            df = pd.DataFrame(rankings)
            rankings = df[elements]

        return rankings

class CollaborationGraphAnalysis(GraphAnalysis):

    def __init__(self, db, graph=None, papers=None, multiple_edges=False, *args, **kwargs):
        self.papers = papers
        self.multiple_edges = multiple_edges
        super().__init__(db, graph=graph, *args, **kwargs)

    def build_graph(self):
        V, E, L, M = self.db.extract_collaboration_graph(papers=self.papers, multiple_edges=self.multiple_edges)
        graph = igraph.Graph(n=len(V))
        for k, v in L.items():
            graph.vs[k] = v
        graph.add_edges(E)
        for k, v in M.items():
            graph.es[k] = v
        return graph

    def default_visual_style(self, graph=None, vertex_color_foo=None, edge_color_foo=None, mode="in", vertex_size=None,
                             layout="fr", vertex_scale=0.4, edge_scale=1, *args, **kwargs):
        visual_style = super().default_visual_style(graph=graph, layout=layout,
                                                    vertex_color_foo=vertex_color_foo,
                                                    edge_color_foo= edge_color_foo,
                                                    mode=mode, vertex_scale=vertex_scale,
                                                    vertex_size=vertex_size,
                                                    edge_scale=edge_scale, *args, **kwargs)
        visual_style["edge_width"] = [1 + edge_scale*e["weight"] for e in self.graph.es]
        visual_style["edge_color"] = ["rgb(255, 102, 102)" if e["weight"] > 1 else "gray" for e in self.graph.es]
        # visual_style["vertex_label"] = graph.vs["name"]
        return visual_style

    @staticmethod
    def color_vertex_pub(graph, colors="Blues", *args, **kwargs):
        pubs = [len(v["papers"]) for v in graph.vs]
        max_val = max(pubs) + 1
        min_val = min(pubs)
        colors = sns.color_palette(colors, max_val-min_val)
        color_dic = {min_val+i: colors[i] for i in range(len(colors))}
        return [color_dic[p] for p in pubs]


# d = d.subgraph([v.index for v in d.vs if len(v["tags"])>1 or "1-1" not in v["tags"]])
#
# for i in d.vs:
#     print(i["tags"])













# d = d.subgraph([v.index for v in d.vs if d.indegree(v.index) > 2] or "0" in v["tags"])
# d = d.subgraph([v.index for v in d.vs if len([n for n in d.neighbors(v) if d.vs[n]["relevant"]]) > 2])
# d = d.subgraph([v.index for v in d.vs if len([n for n in d.neighbors(v) if d.vs[n]["relevant"]]) > 2
#                or (d.indegree(v.index) == 0 and v["relevant"])
#                 or "0" in v["tags"]])


# d = d.subgraph([v.index for v in d.vs if v["relevant"] and v["year"]>=2010])

# d = d.subgraph([v.index for v in d.vs if
#                 len([n for n in d.neighbors(v, mode="in") if d.vs[n]["relevant"]]) > 1
#                 or ((d.indegree(v.index) == 0 or "0" in v["tags"]) and v["relevant"])
#                 ])

#
#
# print(len(d.vs))
#
#
# C = set([v["name"] for v in d.vs if not ("0" in v["tags"] or "-1" in v["tags"])])
#
# cites = [i[1] for i in sorted(zip([len([n for n in d.neighbors(v, mode="out") if d.vs[n]["relevant"]]) for v in d.vs],
#                                    d.vs["name"]), key=lambda x: x[0], reverse=True)][:100]
# degree = [i[1] for i in sorted(zip(d.indegree(), d.vs["name"]), key=lambda x: x[0], reverse=True)][:100]
# pprint(set(cites).intersection(set([v["name"] for v in d.vs if v["relevant"]])).difference(C))

# cites = [i[1] for i in sorted(zip([len([n for n in d.neighbors(v, mode="out") if d.vs[n]["relevant"]]) for v in d.vs],
#                                    d.vs["name"]), key=lambda x: x[0], reverse=True)][:30]
# evcent = [i[1] for i in sorted(zip(d.evcent(), d.vs["name"]), key=lambda x: x[0], reverse=True)][:100]
# closeness = [i[1] for i in sorted(zip(d.closeness(), d.vs["name"]), key=lambda x: x[0], reverse=True)][:100]
# betweenness = [i[1] for i in sorted(zip(d.betweenness(), d.vs["name"]), key=lambda x: x[0], reverse=True)][:100]
# katz = [i[1] for i in sorted(zip(d.katz(), d.vs["name"]), key=lambda x: x[0], reverse=True)]


# X = [degree,cites,evcent,closeness,betweenness]
#
# for i, v1 in enumerate(X):
#     for j, v2 in enumerate(X):
#         print(i,j,":  ", len(set(v1).intersection(v2)))

#
# print(len(set(cites).union(degree)))
# pprint(set(cites).union(degree))
#
# print("")
# pprint(degree)
#
# print("")
# pprint(cites)

# for i in sorted(X, key= lambda x: x[0], reverse=True)[:50]:
#     print(i[0], i[1]["name"])



#
# degree = [i[1].index for i in sorted(zip(d.indegree(), d.vs), key=lambda x: x[0], reverse=True)][:100]
# cites = [i[1].index for i in sorted(zip([len([n for n in d.neighbors(v, mode="out") if d.vs[n]["relevant"]]) for v in d.vs],
#                                    d.vs), key=lambda x: x[0], reverse=True)][:100]
#
# vert = set(cites).union(degree).intersection([i.index for i in d.vs if not i["relevant"]])

#
# stat = {}
# for v in d.vs:
#     if v["relevant"]:
#         if not str.isnumeric(str(v["year"])):
#             print(v["key"],v["name"])
#         if stat.get(v["year"], None) is None:
#             stat[v["year"]] = 0
#         stat[v["year"]] += 1
#
#
# pprint(stat)
#
# nei = []
# for v in vert:
#     nei = nei + [n for n in d.neighbors(v, mode="out") if d.vs[n]["relevant"]]
#
# print(len(set(nei).union(set(vert))))
# for i in set(nei).union(set(vert)):
#     print(d.vs[i]["name"])

# print(len([n for n in d.neighbors(vert, mode="out") if d.vs[n]["relevant"]]))



# for i, v in enumerate([i[1] for i in sorted(zip([len([n for n in d.neighbors(v, mode="out") if d.vs[n]["relevant"]]) for v in d.vs],
#                                    d.vs["name"]), key=lambda x: x[0], reverse=True)]):
#     print(i,v)

