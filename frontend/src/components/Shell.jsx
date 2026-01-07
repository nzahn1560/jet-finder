import { Link, NavLink, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Bars3Icon, XMarkIcon } from "@heroicons/react/24/outline";
import { signOut, getCurrentUser } from "../lib/supabase-auth";

export default function Shell({ children, session }) {
    const [open, setOpen] = useState(false);
    const [user, setUser] = useState(null);
    const [isAdmin, setIsAdmin] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        if (session) {
            loadUser();
        } else {
            setUser(null);
            setIsAdmin(false);
        }
    }, [session]);

    const loadUser = async () => {
        try {
            const currentUser = await getCurrentUser();
            setUser(currentUser);
            setIsAdmin(currentUser?.is_admin || false);
        } catch (error) {
            console.error("Failed to load user:", error);
        }
    };

    const handleSignOut = async () => {
        await signOut();
        navigate("/");
        setUser(null);
        setIsAdmin(false);
    };

    const publicNavItems = [
        { to: "/", label: "Discover" },
    ];

    const authNavItems = [
        { to: "/", label: "Discover" },
        { to: "/sell", label: "List Aircraft" },
        { to: "/dashboard", label: "My Dashboard" },
        { to: "/tools", label: "Tools" },
    ];

    const navItems = session ? authNavItems : publicNavItems;

    return (
        <div className="min-h-screen flex flex-col bg-slate-950 text-white">
            <header className="border-b border-slate-800">
                <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
                    <Link to="/" className="text-xl font-semibold text-white">
                        Jet Finder
                    </Link>
                    <nav className="hidden items-center gap-6 md:flex">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                className={({ isActive }) =>
                                    `text-sm font-medium ${isActive ? "text-brand-500" : "text-slate-300"
                                    }`
                                }
                            >
                                {item.label}
                            </NavLink>
                        ))}
                        {isAdmin && (
                            <NavLink
                                to="/admin"
                                className={({ isActive }) =>
                                    `text-sm font-medium ${isActive ? "text-brand-500" : "text-slate-300"
                                    }`
                                }
                            >
                                Admin
                            </NavLink>
                        )}
                        {session ? (
                            <div className="relative group">
                                <button className="text-sm font-medium text-slate-300 hover:text-white flex items-center gap-2">
                                    {user?.name || user?.email || "Account"}
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </button>
                                <div className="absolute right-0 mt-2 w-48 bg-slate-800 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                                    <div className="py-1">
                                        <Link to="/dashboard" className="block px-4 py-2 text-sm text-slate-200 hover:bg-slate-700">
                                            Dashboard
                                        </Link>
                                        <button
                                            onClick={handleSignOut}
                                            className="block w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-slate-700"
                                        >
                                            Sign Out
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <>
                                <Link to="/login" className="text-sm font-medium text-slate-300 hover:text-white">
                                    Sign In
                                </Link>
                                <Link
                                    to="/signup"
                                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                                >
                                    Sign Up
                                </Link>
                            </>
                        )}
                    </nav>
                    <button
                        className="rounded-md p-2 text-slate-300 hover:text-white md:hidden"
                        onClick={() => setOpen((prev) => !prev)}
                    >
                        {open ? <XMarkIcon className="h-6 w-6" /> : <Bars3Icon className="h-6 w-6" />}
                    </button>
                </div>
                {open && (
                    <div className="space-y-2 border-t border-slate-800 px-4 py-2 md:hidden max-h-[80vh] overflow-y-auto">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                onClick={() => setOpen(false)}
                                className={({ isActive }) =>
                                    `block rounded px-3 py-2 ${isActive ? "bg-slate-800 text-brand-500" : "text-slate-200"
                                    }`
                                }
                            >
                                {item.label}
                            </NavLink>
                        ))}
                        {isAdmin && (
                            <NavLink
                                to="/admin"
                                onClick={() => setOpen(false)}
                                className={({ isActive }) =>
                                    `block rounded px-3 py-2 ${isActive ? "bg-slate-800 text-brand-500" : "text-slate-200"
                                    }`
                                }
                            >
                                Admin
                            </NavLink>
                        )}
                        {session ? (
                            <>
                                <div className="border-t border-slate-700 my-2"></div>
                                <div className="px-3 py-2 text-sm text-slate-400">
                                    {user?.name || user?.email || "Account"}
                                </div>
                                <Link
                                    to="/dashboard"
                                    onClick={() => setOpen(false)}
                                    className="block rounded px-3 py-2 text-slate-200 hover:bg-slate-800"
                                >
                                    Dashboard
                                </Link>
                                <button
                                    onClick={() => {
                                        handleSignOut();
                                        setOpen(false);
                                    }}
                                    className="block w-full text-left rounded px-3 py-2 text-slate-200 hover:bg-slate-800"
                                >
                                    Sign Out
                                </button>
                            </>
                        ) : (
                            <>
                                <div className="border-t border-slate-700 my-2"></div>
                                <Link
                                    to="/login"
                                    onClick={() => setOpen(false)}
                                    className="block rounded px-3 py-2 text-slate-200 hover:bg-slate-800"
                                >
                                    Sign In
                                </Link>
                                <Link
                                    to="/signup"
                                    onClick={() => setOpen(false)}
                                    className="block rounded px-3 py-2 text-white bg-indigo-600 hover:bg-indigo-700 text-center"
                                >
                                    Sign Up
                                </Link>
                            </>
                        )}
                    </div>
                )}
            </header>
            <main className="flex-1">
                <div className="mx-auto max-w-6xl px-4 py-8">{children}</div>
            </main>
            <footer className="border-t border-slate-800 py-6 text-center text-sm text-slate-400">
                © {new Date().getFullYear()} Jet Finder. All rights reserved.
            </footer>
        </div>
    );
}

