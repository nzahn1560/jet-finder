import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/supabase-auth";

const fetchListings = async () => {
    const { data } = await apiClient.get("/api/listings?status=active");
    return data.listings || [];
};

export default function Listings() {
    const { data, isLoading, isError } = useQuery({
        queryKey: ["listings"],
        queryFn: fetchListings
    });

    if (isLoading) {
        return (
            <div className="py-20 text-center text-slate-400">
                Loading available aircraft...
            </div>
        );
    }

    if (isError) {
        return (
            <div className="py-20 text-center text-red-400">
                Unable to load listings. Please try again later.
            </div>
        );
    }

    return (
        <section className="space-y-8">
            <header>
                <h1 className="text-3xl font-semibold">Available Aircraft</h1>
                <p className="mt-2 text-slate-400">
                    Browse curated aircraft listings approved by our team.
                </p>
            </header>

            {data?.length === 0 ? (
                <div className="py-20 text-center text-slate-400">
                    No listings available yet. Check back soon!
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2">
                    {data?.map((listing) => (
                    <article
                        key={listing.id}
                        className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg"
                    >
                        <header className="flex items-start justify-between gap-4">
                            <div>
                                <h2 className="text-xl font-semibold text-white">{listing.title}</h2>
                                <p className="text-sm text-slate-400">
                                    {listing.performance_profile?.manufacturer} •{" "}
                                    {listing.performance_profile?.engine_type}
                                </p>
                            </div>
                            <span className="text-lg font-semibold text-brand-500">
                                ${listing.price_usd.toLocaleString()}
                            </span>
                        </header>
                        <p className="mt-3 text-sm text-slate-300">
                            {listing.description || "No description provided."}
                        </p>
                        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <dt className="text-slate-400">Range</dt>
                                <dd className="font-semibold">
                                    {listing.performance_profile?.range_nm} nm
                                </dd>
                            </div>
                            <div>
                                <dt className="text-slate-400">Cruise Speed</dt>
                                <dd className="font-semibold">
                                    {listing.performance_profile?.cruise_speed_knots} kt
                                </dd>
                            </div>
                            <div>
                                <dt className="text-slate-400">Passengers</dt>
                                <dd className="font-semibold">
                                    {listing.performance_profile?.max_passengers}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-slate-400">Location</dt>
                                <dd className="font-semibold">{listing.location}</dd>
                            </div>
                        </dl>
                        <div className="mt-4 text-right">
                            <a
                                href={`mailto:${listing.contact_email}`}
                                className="rounded-full border border-brand-500 px-4 py-2 text-sm font-medium text-brand-500 transition hover:bg-brand-500 hover:text-white"
                            >
                                Contact Seller
                            </a>
                        </div>
                    </article>
                    ))}
                </div>
            )}
        </section>
    );
}

