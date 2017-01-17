from math import acos, ceil, copysign, cos, degrees, fabs, hypot, pi, radians, sin, sqrt

from reportlab.graphics.shapes import mmult, rotate, translate, transformPoint


def vector_angle(u, v):
    d = hypot(*u) * hypot(*v)
    c = (u[0] * v[0] + u[1] * v[1]) / d
    if c < -1:
        c = -1
    elif c > 1:
        c = 1
    s = u[0] * v[1] - u[1] * v[0]
    return degrees(copysign(acos(c),s))


def end_point_to_center_parameters(x1, y1, x2, y2, fA, fS, rx, ry, phi=0):
    '''
    See http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes F.6.5
    note that we reduce phi to zero outside this routine 
    '''
    rx = fabs(rx)
    ry = fabs(ry)

    # step 1
    if phi:
        phi_rad = radians(phi)
        sin_phi = sin(phi_rad)
        cos_phi = cos(phi_rad)
        tx = 0.5 * (x1 - x2)
        ty = 0.5 * (y1 - y2)
        x1d = cos_phi * tx - sin_phi * ty
        y1d = sin_phi * tx + cos_phi * ty
    else:
        x1d = 0.5 * (x1 - x2)
        y1d = 0.5 * (y1 - y2)

    # step 2
    # we need to calculate
    # (rx*rx*ry*ry-rx*rx*y1d*y1d-ry*ry*x1d*x1d)
    # -----------------------------------------
    #     (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
    #
    # that is equivalent to
    # 
    #          rx*rx*ry*ry 
    # = -----------------------------  -    1
    #   (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
    #
    #              1
    # = -------------------------------- - 1
    #   x1d*x1d/(rx*rx) + y1d*y1d/(ry*ry)
    #
    # = 1/r - 1
    #
    # it turns out r is what they recommend checking
    # for the negative radicand case
    r = x1d * x1d / (rx * rx) + y1d * y1d / (ry * ry)
    if r > 1:
        rr = sqrt(r)
        rx *= rr
        ry *= rr
        r = x1d * x1d / (rx * rx) + y1d * y1d / (ry * ry)
    r = 1 / r - 1
    if -1e-10 < r < 0:
        r = 0
    r = sqrt(r)
    if fA == fS:
        r = -r
    cxd = (r * rx * y1d) / ry
    cyd = -(r * ry *x1d) / rx

    # step 3
    if phi:
        cx = cos_phi * cxd - sin_phi * cyd + 0.5 * (x1 + x2)
        cy = sin_phi * cxd + cos_phi * cyd + 0.5 * (y1 + y2)
    else:
        cx = cxd + 0.5 * (x1 + x2)
        cy = cyd + 0.5 * (y1 + y2)

    # step 4
    theta1 = vector_angle((1, 0), ((x1d - cxd) / rx, (y1d - cyd) / ry))
    dtheta = vector_angle(
        ((x1d - cxd) / rx, (y1d - cyd) / ry),
        ((-x1d - cxd) / rx, (-y1d - cyd) / ry)
    ) % 360
    if fS == 0 and dtheta > 0:
        dtheta -= 360
    elif fS == 1 and dtheta < 0:
        dtheta += 360
    return cx, cy, rx, ry, -theta1, -dtheta


def bezier_arc_from_centre(cx, cy, rx, ry, start_ang=0, extent=90):
    if abs(extent) <= 90:
        nfrag = 1
        frag_angle = float(extent)
    else:
        nfrag = int(ceil(abs(extent) / 90.))
        frag_angle = float(extent) / nfrag

    frag_rad = radians(frag_angle)
    half_rad = frag_rad * 0.5
    kappa = abs(4. / 3. * (1. - cos(half_rad)) / sin(half_rad))

    if frag_angle < 0:
        kappa = -kappa

    point_list = []
    theta1 = radians(start_ang)
    start_rad = theta1 + frag_rad

    c1 = cos(theta1)
    s1 = sin(theta1)
    for i in xrange(nfrag):
        c0 = c1
        s0 = s1
        theta1 = start_rad + i * frag_rad
        c1 = cos(theta1)
        s1 = sin(theta1)
        point_list.append((cx + rx * c0,
                          cy - ry * s0,
                          cx + rx * (c0 - kappa * s0),
                          cy - ry * (s0 + kappa * c0),
                          cx + rx * (c1 + kappa * s1),
                          cy - ry * (s1 - kappa * c1),
                          cx + rx * c1,
                          cy - ry * s1))
    return point_list


def bezier_arc_from_end_points(x1, y1, rx, ry, phi, fA, fS, x2, y2):
    if phi:
        # Our box bezier arcs can't handle rotations directly
        # move to a well known point, eliminate phi and transform the other point
        mx = mmult(rotate(-phi), translate(-x1, -y1))
        tx2, ty2 = transformPoint(mx, (x2, y2))
        # Convert to box form in unrotated coords
        cx, cy, rx, ry, start_ang, extent = end_point_to_center_parameters(0, 0, tx2, ty2, fA, fS, rx, ry)
        bp = bezier_arc_from_centre(cx,cy, rx, ry, start_ang, extent)
        # Re-rotate by the desired angle and add back the translation
        mx = mmult(translate(x1, y1), rotate(phi))
        res = []
        for x1, y1, x2, y2, x3, y3, x4, y4 in bp:
            res.append(
                transformPoint(mx, (x1, y1)) + transformPoint(mx,(x2,y2)) +
                transformPoint(mx, (x3, y3)) + transformPoint(mx, (x4, y4))
            )
        return res
    else:
        cx, cy, rx, ry, start_ang, extent = end_point_to_center_parameters(x1, y1, x2, y2, fA, fS, rx, ry)
        return bezier_arc_from_centre(cx, cy, rx, ry, start_ang, extent)
