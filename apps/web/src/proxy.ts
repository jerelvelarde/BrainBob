import { NextResponse, type NextRequest } from "next/server";
import { requireDemoAccess } from "./lib/demo-access";

export function proxy(request: NextRequest) {
  const denied = requireDemoAccess(request);
  if (denied) return denied;
  const response = NextResponse.next();
  response.headers.set("Cache-Control", "no-store");
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
