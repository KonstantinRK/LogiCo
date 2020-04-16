from fuzzywuzzy import fuzz
import numpy as np
from sklearn.linear_model import LogisticRegression
import csv
import pickle
import os


class StringClassifier:

    def __init__(self, model_path=None, data_path=None, learn=False, learn_from_weak=True):
        self.model_path = model_path
        self.data_path = data_path
        self.learn_from_weak = learn_from_weak
        self.learn = learn if self.data_path is None else False
        self.classifier = None
        self.model = self.default_model

        if model_path is not None and os.path.exists(model_path):
            with open(model_path, "rb") as f:
                self.classifier = pickle.load(f)
        else:
            self.classifier = None

        if self.classifier is not None:
            self.model = self.learned_model

    def set_classifier(self):
        if self.classifier is None:
            if self.model_path is not None and self.data_path is not None and os.path.exists(self.model_path):
                self.learn_classifier()

    def get_model(self, model):
        if model == "very-strong":
            return self.very_strong_trivial_model
        elif model == "strong":
            return self.strong_trivial_model
        elif model == "learn" and self.model_path is not None:
            return self.learned_model
        elif model == "weak":
            return self.weak_trivial_model
        else:
            return self.default_model

    def set_model(self, model):
        self.model = self.get_model(model)

    def equal(self, s1, s2, learn=False, model=None):
        if model is not None:
            model = self.get_model(model)
        else:
            model = self.model
        if learn:
            values = np.array(self.equal_array(s1, s2)).reshape(1, -1)
            if self.learn_from_weak:
                decision = self.weak_trivial_model(values)
            else:
                decision = model(values)
            self.learn_decision(s1, s2, values, decision)
        else:
            return model(self.equal_array(s1, s2))

    def equal_array(self, s1, s2):
        s1 = self.preprocess_string(s1)
        s2 = self.preprocess_string(s2)
        return [fuzz.ratio(s1, s2) / 100, fuzz.partial_ratio(s1, s2) / 100,
                fuzz.token_sort_ratio(s1, s2) / 100, fuzz.token_set_ratio(s1, s2) / 100]

    def learn_decision(self, s1, s2, values, decision):
        if self.data_path is not None:
            with open(self.data_path, "a") as f:
                writer = csv.writer(f)
                if decision and not (values[0] == 1 and values[1] == 1 and values[2] == 1 and values[3] == 1):
                    print("{2} |  {0}   ==   {1}".format(s1, s2, repr(values)))
                    equal = input("y / [n]:").strip()
                    if "y" == equal:
                        decision = True
                    else:
                        decision = False
                writer.writerow(values + [int(decision)])

    def learn_classifier(self):
        if self.data_path is not None:
            if not os.path.exists(self.data_path):
                with open(self.data_path, "w") as f:
                    f.write("")
            with open(self.data_path, "r") as f:
                # [ratio, partial_ratio, token_sort, token_set]
                data = list(csv.reader(f))
            x = np.array([i[:-1] for i in data])
            y = np.array([i[-1] for i in data])
            model = LogisticRegression().fit(x, y)
            with open(self.data_path, "wb") as f:
                pickle.dump(model, f)
            self.classifier = model

    def learned_model(self, x):
        if self.classifier is not None:
            if self.classifier.predict(x)[0] == '0':
                return False
            else:
                return True
        else:
            return None

    def contains_duplicates(self, input_list, learn=True, index=False):
        check_list = [True]*len(input_list)
        duplicates = []
        for i in range(len(input_list)):
            if check_list[i]:
                s1 = input_list[i]
                if index:
                    s1_duplicates = [(i, s1)]
                else:
                    s1_duplicates = [s1]
                for j in range(i+1, len(input_list)):
                    s2 = input_list[j]
                    if self.equal(s1, s2, learn):
                        if index:
                            s1_duplicates.append((i, s1))
                        else:
                            s1_duplicates.append(s2)
                        check_list[j] = False
                duplicates.append(s1_duplicates)

    @staticmethod
    def preprocess_string(s):
        s = s.lower()
        s = s.strip()
        return s

    @staticmethod
    def strong_trivial_model(values):
        check = int(values[0] > 0.90) + int(values[1] > 0.90) + int(values[2] > 0.90) + int(values[3] > 0.90)
        if check > 1:
            return True
        else:
            return False

    @staticmethod
    def default_model(values):
        if values[0] > 0.90 or values[1] > 0.90 or values[2] > 0.90 or values[3] > 0.90:
            return True
        else:
            return False

    @staticmethod
    def very_strong_trivial_model(values):
        if values[0] > 0.97 and values[1] > 0.98 and values[2] > 0.98 and values[3] > 0.96:
            return True
        else:
            return False

    @staticmethod
    def weak_trivial_model(values):
        val = False
        if values[0] > 0.8 or values[1] > 0.98 or values[2] > 0.9 or values[3] > 0.98:
            val = True
        return val

