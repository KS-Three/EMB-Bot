import sys, numpy as np, cv2
d, fx = sys.argv[1], sys.argv[2]
tag = sys.argv[3] if len(sys.argv) > 3 else 'off-on'
m = np.load(f'{d}/{fx}-{tag}-masks.npz')
a, b, ink = m['over_a'], m['over_b'], m['ink_a']
img = np.full(a.shape + (3,), 255, np.uint8)
img[ink] = (200, 200, 200)
img[a & ~b] = (255, 120, 0)      # BGR: blue = OFF only
img[b & ~a] = (0, 0, 230)        # red = ON only
img[a & b] = (160, 0, 160)       # purple = both
ua, ub = m['uns_a'], m['uns_b']
img[ub & ~ua] = (0, 200, 0)      # green = unsewn ON only
img[ua & ~ub] = (0, 200, 200)    # yellow = unsewn OFF only
img[ua & ub] = (0, 100, 0)       # dark green = unsewn both
ys, xs = np.nonzero(ink | a | b)
if len(sys.argv) > 5:
    x0, y0, x1, y1 = map(int, sys.argv[5].split(','))
    img = img[y0:y1, x0:x1]
    ys, xs = np.array([10, img.shape[0]-11]), np.array([10, img.shape[1]-11])
img = img[ys.min()-10:ys.max()+10, xs.min()-10:xs.max()+10]
s = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
if s != 1.0:
    img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
cv2.imwrite(f'{d}/{fx}-{tag}-diff.png', img)
print(img.shape)
