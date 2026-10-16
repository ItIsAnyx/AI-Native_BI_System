import { NavLink, useLocation } from "react-router";

export default function Header () {
    const location = useLocation();
    const from = /^\/(login|register)\/?$/.test(location.pathname)
        ? location.state?.from
        : location;
    return (
        <>
            <header>
                <div>
                    <a href="/">Template</a>

                    <div>
                        <NavLink to="/login" state={{ from }}>Login</NavLink>
                        <NavLink to="/register" state={{ from }}>Register</NavLink>
                    </div>
                </div>
            </header>
        </>
    );
}
