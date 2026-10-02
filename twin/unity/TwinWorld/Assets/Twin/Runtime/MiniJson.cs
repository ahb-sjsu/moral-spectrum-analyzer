using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

// A small JSON reader for the governor service's records (objects become Dictionary<string,object>,
// arrays List<object>, numbers double, true/false bool, null null). Unity's JsonUtility cannot
// read records whose shape varies, and the panel shows them as they arrive.
public static class MiniJson
{
    public static object Parse(string s) { int i = 0; var v = Value(s, ref i); return v; }

    static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }

    static object Value(string s, ref int i)
    {
        Ws(s, ref i);
        if (i >= s.Length) throw new FormatException("unexpected end");
        char c = s[i];
        if (c == '{') { i++; var d = new Dictionary<string, object>(); Ws(s, ref i); if (s[i] == '}') { i++; return d; }
            while (true) { Ws(s, ref i); string k = Str(s, ref i); Ws(s, ref i); i++; d[k] = Value(s, ref i); Ws(s, ref i); if (s[i] == ',') { i++; continue; } i++; return d; } }
        if (c == '[') { i++; var l = new List<object>(); Ws(s, ref i); if (s[i] == ']') { i++; return l; }
            while (true) { l.Add(Value(s, ref i)); Ws(s, ref i); if (s[i] == ',') { i++; continue; } i++; return l; } }
        if (c == '"') return Str(s, ref i);
        if (s.Substring(i).StartsWith("true")) { i += 4; return true; }
        if (s.Substring(i).StartsWith("false")) { i += 5; return false; }
        if (s.Substring(i).StartsWith("null")) { i += 4; return null; }
        int j = i; while (j < s.Length && "+-0123456789.eE".IndexOf(s[j]) >= 0) j++;
        var num = double.Parse(s.Substring(i, j - i), CultureInfo.InvariantCulture); i = j; return num;
    }

    static string Str(string s, ref int i)
    {
        var b = new StringBuilder(); i++;
        while (s[i] != '"')
        {
            if (s[i] == '\\')
            {
                i++;
                char e = s[i];
                if (e == 'u') { b.Append((char)Convert.ToInt32(s.Substring(i + 1, 4), 16)); i += 4; }
                else b.Append(e == 'n' ? '\n' : e == 't' ? '\t' : e == 'r' ? '\r' : e == 'b' ? '\b' : e == 'f' ? '\f' : e);
            }
            else b.Append(s[i]);
            i++;
        }
        i++;
        return b.ToString();
    }

    // write a value built from dictionaries, lists, strings, numbers and booleans
    public static string Write(object o)
    {
        var b = new StringBuilder(); W(b, o); return b.ToString();
    }

    static void W(StringBuilder b, object o)
    {
        switch (o)
        {
            case null: b.Append("null"); break;
            case string s: Q(b, s); break;
            case bool x: b.Append(x ? "true" : "false"); break;
            case float f: b.Append(f.ToString("0.###", CultureInfo.InvariantCulture)); break;
            case double d: b.Append(d.ToString("0.###", CultureInfo.InvariantCulture)); break;
            case int i: b.Append(i.ToString(CultureInfo.InvariantCulture)); break;
            case long l: b.Append(l.ToString(CultureInfo.InvariantCulture)); break;
            case System.Collections.IDictionary dict:
            {
                b.Append('{'); bool first = true;
                foreach (System.Collections.DictionaryEntry kv in dict)
                { if (!first) b.Append(','); first = false; Q(b, kv.Key.ToString()); b.Append(':'); W(b, kv.Value); }
                b.Append('}'); break;
            }
            case System.Collections.IEnumerable list:
            {
                b.Append('['); bool first = true;
                foreach (var x in list) { if (!first) b.Append(','); first = false; W(b, x); }
                b.Append(']'); break;
            }
            default: Q(b, o.ToString()); break;
        }
    }

    static void Q(StringBuilder b, string s)
    {
        // written with character codes so no escape sequence can be mangled in transit
        const char BS = (char)92, DQ = (char)34;
        b.Append(DQ);
        foreach (char c in s)
        {
            if (c == DQ || c == BS) b.Append(BS).Append(c);
            else if (c == (char)10) b.Append(BS).Append('n');
            else if (c == (char)13) b.Append(BS).Append('r');
            else if (c == (char)9) b.Append(BS).Append('t');
            else if (c < (char)32) b.Append(BS).Append('u').Append(((int)c).ToString("x4"));
            else b.Append(c);
        }
        b.Append(DQ);
    }

    public static Dictionary<string, object> Obj(object o) => o as Dictionary<string, object> ?? new Dictionary<string, object>();
    public static List<object> Arr(object o) => o as List<object> ?? new List<object>();
    public static string S(object o) => o == null ? "" : o is double d ? d.ToString("0.###", CultureInfo.InvariantCulture) : o.ToString();

    // a compact, readable rendering of any value, for the detail tree
    public static string Show(object o, int depth = 0)
    {
        if (o is Dictionary<string, object> d)
        {
            var parts = new List<string>(); foreach (var kv in d) parts.Add(kv.Key + "=" + Show(kv.Value, depth + 1));
            return "{" + string.Join(", ", parts) + "}";
        }
        if (o is List<object> l) { var parts = new List<string>(); foreach (var x in l) parts.Add(Show(x, depth + 1)); return "[" + string.Join(", ", parts) + "]"; }
        return S(o);
    }
}
