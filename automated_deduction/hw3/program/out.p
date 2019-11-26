% Refutation found. Thanks to Tanya!
% SZS status Theorem for group
% SZS output start Proof for group
1. ! [X0] : mult(e,X0) = X0 [input]
2. ! [X0] : e = mult(inverse(X0),X0) [input]
3. ! [X0,X1,X2] : mult(X0,mult(X1,X2)) = mult(mult(X0,X1),X2) [input]
4. ! [X0] : mult(X0,e) = X0 [input]
5. ~! [X0] : mult(X0,e) = X0 [negated conjecture 4]
6. ? [X0] : mult(X0,e) != X0 [ennf transformation 5]
7. ? [X0] : mult(X0,e) != X0 => mult(sK0,e) != sK0 [choice axiom]
8. mult(sK0,e) != sK0 [skolemisation 6,7]
9. mult(e,X0) = X0 [cnf transformation 1]
10. e = mult(inverse(X0),X0) [cnf transformation 2]
11. mult(X0,mult(X1,X2)) = mult(mult(X0,X1),X2) [cnf transformation 3]
12. mult(sK0,e) != sK0 [cnf transformation 8]
14. mult(e,X3) = mult(inverse(X2),mult(X2,X3)) [superposition 11,10]
16. mult(inverse(X2),mult(X2,X3)) = X3 [forward demodulation 14,9]
20. mult(inverse(inverse(X1)),e) = X1 [superposition 16,10]
22. mult(X5,X6) = mult(inverse(inverse(X5)),X6) [superposition 16,16]
33. mult(X3,e) = X3 [superposition 22,20]
53. sK0 != sK0 [superposition 12,33]
54. $false [trivial inequality removal 53]
% SZS output end Proof for group
% ------------------------------
% Version: Vampire 4.2.2 (commit e1949dd on 2017-12-14 18:39:21 +0000)
% Termination reason: Refutation

% Memory used [KB]: 383
% Time elapsed: 0.019 s
% ------------------------------
% ------------------------------
