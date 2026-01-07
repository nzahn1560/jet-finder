import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useState } from "react";

import { adminToken } from "../lib/auth";

const fetchPendingListings = async () => {
    const { data } = await axios.get("/api/admin/listings/", {
        headers: { Authorization: `Bearer ${adminToken}` }
    });
    return data;
};

const updateStatus = async ({ id, status, reason }) => {
    const { data } = await axios.post(
        `/api/admin/listings/${id}/status`,
        { status, reason },
        {
            headers: { Authorization: `Bearer ${adminToken}` }
        }
    );
    return data;
};

export default function AdminDashboard() {
    const queryClient = useQueryClient();
    const [rejectionNotes, setRejectionNotes] = useState({});

    const { data, isLoading, isError } = useQuery({
        queryKey: ["pending-listings"],
        queryFn: fetchPendingListings
    });

    const mutation = useMutation({
        mutationFn: updateStatus,
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["pending-listings"] });
            queryClient.invalidateQueries({ queryKey: ["listings"] });
            setRejectionNotes((prev) => {
                const next = { ...prev };
                delete next[variables.id];
                return next;
            });
        }
    });

    if (isLoading) {
        return <p className="py-20 text-center text-slate-400">Loading pending listings...</p>;
    }

    if (isError) {
        return <p className="py-20 text-center text-red-400">Unable to load admin data.</p>;
    }

    return (
        <section className="space-y-8">
            <header>
                <h1 className="text-3xl font-semibold">Admin Review</h1>
                <p className="text-slate-400">Approve or reject pending aircraft listings.</p>
            </header>

            <div className="space-y-4">
                {data?.length === 0 && (
                    <div className="rounded-xl border border-slate-800 p-6 text-center text-slate-400">
                        No listings awaiting review.
                    </div>
                )}
                {data?.map((listing) => (
                    <article key={listing.id} className="rounded-2xl border border-yellow-500/20 bg-slate-900/70 p-6">
                        <header className="flex items-center justify-between gap-4">
                            <div>
                                <h2 className="text-xl font-semibold text-white">{listing.title}</h2>
                                <p className="text-sm text-slate-400">
                                    {listing.performance_profile?.manufacturer} • {listing.engine_type}
                                </p>
                            </div>
                            <span className="text-lg font-semibold text-yellow-500">
                                ${listing.price_usd.toLocaleString()}
                            </span>
                        </header>
                        <p className="mt-3 text-slate-300">{listing.description}</p>
                        <div className="mt-4 grid gap-4 md:grid-cols-3 text-sm text-slate-400">
                            <div>
                                <strong className="text-slate-200">Location</strong>
                                <p>{listing.location}</p>
                            </div>
                            <div>
                                <strong className="text-slate-200">Plan</strong>
                                <p>{listing.payment_plan === "semiannual" ? "6 month" : "Monthly"}</p>
                            </div>
                            <div>
                                <strong className="text-slate-200">Contact</strong>
                                <p>{listing.contact_email}</p>
                            </div>
                        </div>
                        <div className="mt-4">
                            <label className="text-sm text-slate-400">Review notes (optional)</label>
                            <textarea
                                rows={2}
                                value={rejectionNotes[listing.id] ?? ""}
                                onChange={(event) =>
                                    setRejectionNotes((prev) => ({
                                        ...prev,
                                        [listing.id]: event.target.value
                                    }))
                                }
                                className="mt-2 w-full rounded-xl border border-slate-700 bg-transparent px-3 py-2 text-sm text-white"
                                placeholder="Share a quick reason if rejecting this listing..."
                            />
                        </div>
                        <div className="mt-6 flex flex-col gap-3 md:flex-row md:justify-end">
                            <button
                                className="rounded-xl border border-red-500 px-4 py-2 text-red-400"
                                onClick={() =>
                                    mutation.mutate({
                                        id: listing.id,
                                        status: "rejected",
                                        reason: rejectionNotes[listing.id] || "Listing rejected by admin."
                                    })
                                }
                            >
                                Reject
                            </button>
                            <button
                                className="rounded-xl bg-green-500 px-4 py-2 font-semibold text-white"
                                onClick={() =>
                                    mutation.mutate({
                                        id: listing.id,
                                        status: "active",
                                        reason: rejectionNotes[listing.id] || undefined
                                    })
                                }
                            >
                                Approve & Publish
                            </button>
                        </div>
                    </article>
                ))}
            </div>
        </section>
    );
}

